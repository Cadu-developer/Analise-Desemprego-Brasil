"""Dashboard escolar: trabalho e população empregada no Brasil.
Fontes: IBGE/SIDRA (PNAD Contínua 4093, 4095, 5434; Censo 2022 10284, 10292).
"""
import pandas as pd
import plotly.express as px
import streamlit as st
import requests

st.set_page_config(page_title="Trabalho e Emprego no Brasil", layout="wide")
st.title("📊 Trabalho e População Empregada")
st.caption("Startup de análise de dados • IBGE • Todos os 26 estados e o Distrito Federal")

# Siglas e códigos oficiais das Unidades da Federação (IBGE).
UF = {
    "AC": 12, "AL": 27, "AP": 16, "AM": 13, "BA": 29, "CE": 23,
    "DF": 53, "ES": 32, "GO": 52, "MA": 21, "MT": 51, "MS": 50,
    "MG": 31, "PA": 15, "PB": 25, "PR": 41, "PE": 26, "PI": 22,
    "RJ": 33, "RN": 24, "RS": 43, "RO": 11, "RR": 14, "SC": 42,
    "SP": 35, "SE": 28, "TO": 17,
}
ESTADOS = {str(c): sigla for sigla, c in UF.items()}
ESCOLAS = {
    "Todas": [],
    "Sem instrução / fundamental incompleto": [
        "Sem instrução e menos de 1 ano de estudo",
        "Ensino fundamental incompleto ou equivalente",
    ],
    "Fundamental completo / médio incompleto": [
        "Ensino fundamental completo ou equivalente",
        "Ensino médio incompleto ou equivalente",
    ],
    "Médio completo / superior incompleto": [
        "Ensino médio completo ou equivalente",
        "Ensino superior incompleto ou equivalente",
    ],
    "Superior completo": ["Ensino superior completo ou equivalente"],
}
ESCOLA_CENSO = {
    "Todas": "Total",
    "Sem instrução / fundamental incompleto": "Sem instrução e fundamental incompleto",
    "Fundamental completo / médio incompleto": "Fundamental completo e médio incompleto",
    "Médio completo / superior incompleto": "Médio completo e superior incompleto",
    "Superior completo": "Superior completo",
}
FAIXAS = [
    "Sem rendimento", "Até 1/4 de salário mínimo",
    "Mais de 1/4 a 1/2 salário mínimo", "Mais de 1/2 a 1 salário mínimo",
    "Mais de 1 a 2 salários mínimos", "Mais de 2 a 3 salários mínimos",
    "Mais de 3 a 5 salários mínimos", "Mais de 5 a 10 salários mínimos",
    "Mais de 10 a 15 salários mínimos", "Mais de 15 a 20 salários mínimos",
    "Mais de 20 salários mínimos",
]

@st.cache_data(ttl=86400, show_spinner="Consultando dados oficiais do IBGE...")
def sidra(tabela, variaveis, periodos, dimensao="", nivel="n3/all"):
    """Lê uma pequena tabela do IBGE sem necessidade de planilhas locais."""
    url = (f"https://apisidra.ibge.gov.br/values/t/{tabela}/{nivel}/"
           f"v/{variaveis}/p/{periodos}/{dimensao}?formato=json")
    resposta = requests.get(url, timeout=45, headers={"User-Agent": "DashboardEscolar/1.0"})
    resposta.raise_for_status()
    conteudo = resposta.json()
    if not isinstance(conteudo, list) or len(conteudo) < 2:
        raise ValueError(f"Tabela {tabela} sem resultados: {str(conteudo)[:200]}")
    dados = pd.DataFrame(conteudo[1:]).rename(columns=conteudo[0])
    dados["Valor"] = pd.to_numeric(
        dados["Valor"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
    return dados.dropna(subset=["Valor"])


def coluna(dados, nome):
    """Acha uma dimensão na resposta do SIDRA (sem usar o código da coluna)."""
    encontrados = [c for c in dados.columns if c == nome]
    if not encontrados:
        encontrados = [c for c in dados.columns if nome.lower() in c.lower()
                       and "(Código)" not in c]
    if not encontrados:
        raise ValueError(f"Dimensão '{nome}' não encontrada na resposta do IBGE")
    return encontrados[0]


def preparo(dados, referencia="UF"):
    """Padroniza códigos de UF, sexo, trimestre e variável."""
    d = dados.copy()
    if referencia == "UF":
        d["UF"] = d[coluna(d, "Unidade da Federação (Código)")].astype(str).map(ESTADOS)
        d = d[d["UF"].notna()]
    d["Variavel"] = d[coluna(d, "Variável (Código)")].astype(str)
    if "Trimestre" in d.columns:
        d["Ano"] = d[coluna(d, "Trimestre (Código)")].astype(str).str[:4]
    elif "Ano (Código)" in d.columns:
        d["Ano"] = d["Ano (Código)"].astype(str).str[:4]
    return d


def setor_pnad(nome):
    t = str(nome).lower()
    if t == "total" or "indústria de transformação" in t or "mal definidas" in t:
        return None  # Indústria de transformação já faz parte de Indústria geral.
    if "agricultura" in t or "pecuária" in t:
        return "Agro"
    if "indústria geral" in t or "construção" in t:
        return "Indústria"
    return "Serviços"


def setor_censo(nome):
    t = str(nome).lower()
    if t == "total":
        return "Todos"
    if "agricultura" in t or "pecuária" in t:
        return "Agro"
    if any(x in t for x in ("indústria", "indústrias", "construção", "eletricidade",
                             "água, esgoto", "atividades de gestão de resíduos")):
        return "Indústria"
    return "Serviços"


st.sidebar.header("Filtros")
uf = st.sidebar.selectbox("UF", ["Todas"] + sorted(UF))
sexo = st.sidebar.selectbox("Sexo", ["Total", "Homens", "Mulheres"])
escola = st.sidebar.selectbox("Escolaridade", list(ESCOLAS))
setor = st.sidebar.selectbox("Setor econômico", ["Todos", "Agro", "Indústria", "Serviços"])
st.sidebar.caption("Os filtros valem para os gráficos que possuem esse recorte no IBGE.")

# PNAD Contínua: 1º trimestre de cada ano, diretamente da tabela 4093.
try:
    trabalho = preparo(sidra(4093, "4099,4092,4088,4090,4723,12466",
                            "201201,202201", "c2/all"))
    trabalho["Sexo"] = trabalho[coluna(trabalho, "Sexo")].str.strip()
    trabalho = trabalho.pivot_table(
        index=["UF", "Ano", "Sexo"], columns="Variavel", values="Valor", aggfunc="first"
    ).reset_index()
    # 4099 = taxa de desocupação; 4092 = desocupados (mil pessoas).
    if not {"4099", "4092"}.issubset(trabalho.columns):
        raise ValueError("Indicadores essenciais indisponíveis na tabela 4093")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.error("Não foi possível ler a PNAD no IBGE. Confira sua conexão e reinicie o app.")
    st.code(str(erro))
    st.stop()

base = trabalho[trabalho["Sexo"] == sexo].copy()
if uf != "Todas":
    base = base[base["UF"] == uf]

st.subheader("1. Desemprego por estado: 2012 × 2022")
st.caption("PNAD Contínua • 1º trimestre de 2012 e 1º trimestre de 2022 • Taxa de desocupação (%).")
fig = px.bar(base, x="UF", y="4099", color="Ano", barmode="group",
             labels={"4099": "Taxa de desemprego (%)", "UF": "Estado", "Ano": "Ano"},
             color_discrete_sequence=["#2563eb", "#f59e0b"])
fig.update_layout(xaxis={"categoryorder": "category ascending"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("2. Comparação por gênero")
por_sexo = trabalho[trabalho["Sexo"].isin(["Homens", "Mulheres"])].copy()
if uf != "Todas":
    por_sexo = por_sexo[por_sexo["UF"] == uf]
fig = px.bar(por_sexo, x="UF", y="4099", color="Sexo", barmode="group",
             facet_col="Ano", labels={"4099": "Taxa (%)", "UF": "Estado"},
             color_discrete_sequence=["#2563eb", "#db2777"])
st.plotly_chart(fig, use_container_width=True)

st.subheader("3. Qual estado reduziu mais a população desempregada?")
# A pergunta exige comparar a quantidade, não somente a taxa.
contagem = trabalho[trabalho["Sexo"] == "Total"].pivot_table(
    index="UF", columns="Ano", values="4092", aggfunc="first"
).dropna(subset=["2012", "2022"])
contagem["Mudança (mil pessoas)"] = contagem["2022"] - contagem["2012"]
reducoes = contagem[contagem["Mudança (mil pessoas)"] < 0]
if reducoes.empty:
    st.info("Nenhuma UF teve redução no número estimado de desocupados entre os primeiros trimestres de 2012 e 2022.")
else:
    melhor = reducoes["Mudança (mil pessoas)"].idxmin()
    queda = reducoes.loc[melhor, "Mudança (mil pessoas)"]
    st.success(f"Maior redução: **{melhor}**, aproximadamente **{abs(queda):,.0f} mil** desocupados a menos.")

contagem_tabela = contagem if uf == "Todas" else contagem.loc[contagem.index == uf]
st.dataframe(contagem_tabela.reset_index().rename(columns={"2012": "2012 (mil)",
             "2022": "2022 (mil)"}).round(1), use_container_width=True, hide_index=True)
st.caption("Os números são estimativas amostrais em milhares de pessoas. 'Redução' é diferença entre dois períodos, não prova de causalidade.")

# Escolaridade: a PNAD permite escolaridade OU sexo nesta tabela, mas não seu cruzamento.
if escola != "Todas":
    st.subheader("4. Desemprego por escolaridade")
    try:
        edu = preparo(sidra(4095, "4092,4088", "201201,202201", "c1568/all"))
        edu["Escolaridade"] = edu[coluna(edu, "Nível de instrução")]
        edu = edu[edu["Escolaridade"].isin(ESCOLAS[escola])]
        edu = edu.pivot_table(index=["UF", "Ano"], columns="Variavel", values="Valor",
                               aggfunc="sum").reset_index()
        edu["Taxa (%)"] = 100 * edu["4092"] / edu["4088"]
        if uf != "Todas":
            edu = edu[edu["UF"] == uf]
        fig = px.bar(edu, x="UF", y="Taxa (%)", color="Ano", barmode="group")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Taxa calculada a partir de desocupados ÷ força de trabalho, somando os níveis escolares da faixa escolhida. Não cruzada com sexo.")
    except (requests.RequestException, ValueError, KeyError, ZeroDivisionError) as erro:
        st.warning(f"Os dados de escolaridade não puderam ser carregados: {erro}")

st.subheader("5. Formalidade × informalidade (barras agrupadas)")
inform = trabalho[(trabalho["Ano"] == "2022") & (trabalho["Sexo"] == sexo)].copy()
if uf != "Todas":
    inform = inform[inform["UF"] == uf]
if "12466" in inform.columns:
    inform["Informal"] = inform["12466"]
    inform["Formal"] = 100 - inform["Informal"]
    graf = inform.melt(id_vars=["UF"], value_vars=["Formal", "Informal"],
                       var_name="Situação", value_name="Percentual")
    fig = px.bar(graf, x="UF", y="Percentual", color="Situação", barmode="group",
                 color_discrete_sequence=["#16a34a", "#f97316"])
    st.plotly_chart(fig, use_container_width=True)
    st.caption("PNAD 1º trimestre de 2022. 'Formal' aqui é o complemento da taxa de informalidade do IBGE; não representa apenas carteira assinada. Este gráfico não é dividido por setor ou escolaridade.")
else:
    st.warning("O IBGE não retornou taxa de informalidade para esse período.")

st.subheader("6. Pessoas ocupadas por setor")
try:
    atividades = preparo(sidra(5434, "4090", "202201", "c888/all"))
    atividades["Ramo"] = atividades[coluna(atividades, "Grupamentos de atividades")]
    atividades["Setor"] = atividades["Ramo"].map(setor_pnad)
    atividades = atividades[atividades["Setor"].notna()]
    if setor != "Todos":
        atividades = atividades[atividades["Setor"] == setor]
    if uf != "Todas":
        atividades = atividades[atividades["UF"] == uf]
    dados_setor = atividades.groupby(["UF", "Setor"], as_index=False)["Valor"].sum()
    fig = px.bar(dados_setor, x="UF", y="Valor", color="Setor", barmode="group",
                 labels={"Valor": "Pessoas ocupadas (mil)"})
    st.plotly_chart(fig, use_container_width=True)
    st.caption("PNAD 1º trimestre de 2022. 'Serviços' inclui comércio; 'Indústria' inclui construção. Este setor é do emprego ocupado, não do desemprego. Sem divisão por sexo na tabela consultada.")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar a divisão por setor: {erro}")

st.subheader("7. Distribuição dos rendimentos do trabalho")
st.caption("Censo Demográfico 2022, distribuição de pessoas ocupadas por faixa de salários mínimos (dados agrupados, não salários individuais).")
nivel = "n1/all" if uf == "Todas" else f"n3/{UF[uf]}"
try:
    renda = preparo(sidra(10292, "13600", "2022", "c2/all/c11915/all", nivel), "Brasil")
    renda["Sexo"] = renda[coluna(renda, "Sexo")].str.strip()
    renda["Faixa"] = renda[coluna(renda, "Classes de rendimento")].str.strip()
    renda = renda[(renda["Sexo"] == sexo) & (renda["Faixa"].isin(FAIXAS))]
    renda["Faixa"] = pd.Categorical(renda["Faixa"], categories=FAIXAS, ordered=True)
    renda = renda.sort_values("Faixa")
    fig = px.bar(renda, x="Faixa", y="Valor", labels={"Valor": "Trabalhadores (%)", "Faixa": "Rendimento"},
                 color_discrete_sequence=["#2563eb"])
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)
    # O Censo também informa média e mediana oficiais para essa mesma UF e sexo.
    resumo = preparo(sidra(10284, "13536,13537", "2022",
                           "c2/all/c1568/all/c11805/all", nivel), "Brasil")
    resumo["Sexo"] = resumo[coluna(resumo, "Sexo")].str.strip()
    resumo["Escolaridade"] = resumo[coluna(resumo, "Nível de instrução")].str.strip()
    resumo["Ramo"] = resumo[coluna(resumo, "Seção de atividade")].str.strip()
    resumo = resumo[(resumo["Sexo"] == sexo) & (resumo["Escolaridade"] == "Total") &
                    (resumo["Ramo"] == "Total")]
    medidas = dict(zip(resumo["Variavel"], resumo["Valor"]))
    if "13536" in medidas and "13537" in medidas:
        m1, m2 = st.columns(2)
        m1.metric("Média mensal", f"R$ {medidas['13536']:,.0f}")
        m2.metric("Mediana mensal", f"R$ {medidas['13537']:,.0f}")
        if medidas["13536"] > medidas["13537"]:
            st.info("A média é maior que a mediana: os rendimentos mais altos puxam a média para cima (assimetria à direita).")
    st.caption("Faixas do Censo 2022. Setor e escolaridade não se aplicam a este histograma, pois a tabela de faixas não contém esses cruzamentos.")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar o histograma de rendimentos: {erro}")

st.subheader("8. Média × mediana e paridade salarial")
try:
    salario = preparo(sidra(10284, "13536,13537", "2022",
                            "c2/all/c1568/all/c11805/all", nivel), "Brasil")
    salario["Sexo"] = salario[coluna(salario, "Sexo")].str.strip()
    salario["Escolaridade"] = salario[coluna(salario, "Nível de instrução")].str.strip()
    salario["Ramo"] = salario[coluna(salario, "Seção de atividade")].str.strip()
    salario["Setor"] = salario["Ramo"].map(setor_censo)
    salario = salario[salario["Escolaridade"] == ESCOLA_CENSO[escola]]
    if setor == "Todos":
        salario = salario[salario["Ramo"] == "Total"]
    else:
        salario = salario[salario["Setor"] == setor]
        salario = salario[salario["Ramo"] != "Total"]
    if sexo != "Total":
        salario = salario[salario["Sexo"] == sexo]
    else:
        salario = salario[salario["Sexo"].isin(["Homens", "Mulheres"])]
    salario["Indicador"] = salario["Variavel"].map({"13536": "Média", "13537": "Mediana"})
    salario = salario[salario["Indicador"].notna()]
    if not salario.empty:
        fig = px.bar(salario, x="Ramo" if setor != "Todos" else "Sexo",
                     y="Valor", color="Indicador", barmode="group",
                     facet_col="Sexo" if setor != "Todos" and sexo == "Total" else None,
                     labels={"Valor": "Rendimento nominal mensal (R$)", "Ramo": "Atividade"})
        fig.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(salario[["Sexo", "Escolaridade", "Ramo", "Indicador", "Valor"]].round(0),
                     use_container_width=True, hide_index=True)
        st.caption("Censo 2022: média e mediana oficiais por sexo, instrução e atividade. Se a média supera a mediana, rendimentos altos elevam a média. Para setores com vários ramos, os indicadores são exibidos por ramo, sem somar medianas.")
    else:
        st.info("Sem dados disponíveis para a combinação escolhida.")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar média e mediana: {erro}")

st.subheader("9. Propostas da mesa de negociação")
st.write("**Márcia (Governo):** ampliar fiscalização e qualificação para o trabalho formal.")
st.write("**Renato (Indústria):** incentivar contratações, capacitação e produtividade.")
st.write("**Sílvia (Sebrae):** orientar pequenas empresas na formalização e promover transparência salarial.")

st.subheader("📰 Notícias recentes")
st.markdown(
    "- **PNAD Contínua (30/10/2026):** [taxa de desocupação de 5,2% no 3º trimestre](https://agenciagov.ebc.com.br/noticias/202610/taxa-de-desemprego-tem-queda-e-alcanca-menor-resultado-para-setembro-em-14-anos).\n"
    "- **Novo Caged (04/11/2026):** [121,3 mil vagas formais em setembro](https://agenciagov.ebc.com.br/noticias/202611/brasil-gera-121-3-mil-empregos-formais-em-setembro-e-saldo-no-ano-chega-a-1-24-milhao-de-novos-postos-com-carteira-assinada)."
)

st.subheader("📷 Trabalhadores brasileiros")
c1, c2 = st.columns(2)
with c1:
    st.image("https://commons.wikimedia.org/wiki/Special:FilePath/Fabrica_Farinha_Acari.jpg?width=800",
             caption="Trabalho industrial — Casteliane / Wikimedia Commons (CC BY-SA 3.0).", use_container_width=True)
with c2:
    st.image("https://commons.wikimedia.org/wiki/Special:FilePath/Agricultura_familiar_(15643548663).jpg?width=800",
             caption="Agricultura familiar — Sergio Amaral / MDS (CC BY-SA 2.0).", use_container_width=True)

st.markdown("---")
st.caption("Fontes oficiais: [SIDRA 4093](https://sidra.ibge.gov.br/tabela/4093) · "
           "[SIDRA 4095](https://sidra.ibge.gov.br/tabela/4095) · "
           "[SIDRA 5434](https://sidra.ibge.gov.br/tabela/5434) · "
           "[Censo 10292](https://sidra.ibge.gov.br/tabela/10292) · "
           "[Censo 10284](https://sidra.ibge.gov.br/tabela/10284). "
           "PNAD e Censo são pesquisas diferentes; não compare diretamente seus totais.")
