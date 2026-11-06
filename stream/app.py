from pathlib import Path
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Trabalho e Desocupação", layout="wide")
st.title("📊 Trabalho e População Desocupada")
st.write("Comparação entre o 1º trimestre de 2012 e o 1º trimestre de 2026, por estado e sexo.")

# As duas planilhas originais permanecem no projeto.
PASTA = Path(__file__).resolve().parent


@st.cache_data
def carregar_dados():
    def caminho(nome):
        # Funciona com planilhas dentro de stream/ ou na raiz do repositório.
        arquivo = PASTA / nome
        if not arquivo.exists():
            arquivo = PASTA.parent / nome
        return arquivo

    df_2012 = pd.read_excel(caminho("Tabela5-sem_emprego_2012.xlsx"), engine="calamine")
    df_2026 = pd.read_excel(caminho("Tabela5-sem_emprego_2026.xlsx"), engine="calamine")

    # As colunas 4 e 5 mostram a distribuição percentual dos desocupados por sexo.
    for df, ano in [(df_2012, 2012), (df_2026, 2026)]:
        df.columns = ["UF", "Código", "Estado", "Homens", "Mulheres"]
        df["Ano"] = ano

    return pd.concat([df_2012, df_2026], ignore_index=True)


dados = carregar_dados()

# Filtros pedidos no enunciado. Cada um atua nas seções com dados disponíveis.
ESCOLARIDADES = [
    "Todas",
    "Sem instrução e menos de 1 ano de estudo",
    "Ensino fundamental incompleto ou equivalente",
    "Ensino fundamental completo ou equivalente",
    "Ensino médio incompleto ou equivalente",
    "Ensino médio completo ou equivalente",
    "Ensino superior incompleto ou equivalente",
    "Ensino superior completo ou equivalente",
]
st.sidebar.header("Filtros")
uf = st.sidebar.selectbox("UF", ["Todas"] + sorted(dados["UF"].unique().tolist()))
sexo = st.sidebar.selectbox("Sexo", ["Homens", "Mulheres"])
ano_grafico = st.sidebar.selectbox("Ano para o 2º gráfico", [2012, 2026], index=1)
setor = st.sidebar.selectbox("Setor econômico", ["Todos", "Agro", "Indústria", "Serviços"])
escolaridade = st.sidebar.selectbox("Escolaridade", ESCOLARIDADES)
st.sidebar.caption("Setor e escolaridade valem apenas para análises que possuem esses recortes.")

filtrado = dados if uf == "Todas" else dados[dados["UF"] == uf]

st.info(
    "As planilhas Excel mostram a **participação de homens e mulheres entre "
    "os desocupados**, e não a taxa geral de desemprego. As taxas oficiais estão abaixo."
)

col1, col2 = st.columns(2)
col1.metric("UFs selecionadas", filtrado["UF"].nunique())
col2.metric("Anos comparados", "2012 e 2026")

# 1. Primeiro gráfico original: participação do sexo escolhido nos dois anos.
st.subheader(f"1. Participação dos desocupados — 2012 × 2026 — {sexo}")
fig1 = px.bar(
    filtrado.assign(Ano=filtrado["Ano"].astype(str)),
    x="UF", y=sexo, color="Ano", barmode="group",
    color_discrete_sequence=["#377db4", "#f59e0b"],
    labels={sexo: "Participação entre desocupados (%)", "UF": "Estado", "Ano": "Ano"},
    hover_data=["Estado"],
)
fig1.update_layout(yaxis_range=[0, 100])
st.plotly_chart(fig1, use_container_width=True)

# 2. Segundo gráfico original: composição dos desocupados.
st.subheader(f"2. Distribuição dos desocupados por sexo — {ano_grafico}")
so_ano = filtrado[filtrado["Ano"] == ano_grafico]
fig2 = px.bar(
    so_ano, x="UF", y=["Homens", "Mulheres"], barmode="stack",
    labels={"value": "Participação (%)", "variable": "Sexo", "UF": "Estado"},
    color_discrete_sequence=["#377db4", "#e879a5"],
)
fig2.update_layout(yaxis_range=[0, 100])
st.plotly_chart(fig2, use_container_width=True)

# 3. Tabela original: variações da participação por sexo.
a = filtrado[filtrado["Ano"] == 2012][["UF", "Estado", "Homens", "Mulheres"]]
b = filtrado[filtrado["Ano"] == 2026][["UF", "Homens", "Mulheres"]]
comparacao = a.merge(b, on="UF", suffixes=(" 2012", " 2026"))
comparacao["Mudança homens (p.p.)"] = comparacao["Homens 2026"] - comparacao["Homens 2012"]
comparacao["Mudança mulheres (p.p.)"] = comparacao["Mulheres 2026"] - comparacao["Mulheres 2012"]

st.subheader("3. Tabela comparativa")
st.dataframe(comparacao.round(1), use_container_width=True, hide_index=True)
if not comparacao.empty:
    menor_h = comparacao.loc[comparacao["Mudança homens (p.p.)"].idxmin()]
    st.write(
        "**Maior queda na participação masculina entre os desocupados:** "
        f"{menor_h['Estado']} ({menor_h['Mudança homens (p.p.)']:+.1f} p.p.)."
    )

# -----------------------------------------------------------------------------
# NOVAS SEÇÕES: dados oficiais para os critérios que faltavam no enunciado.
# Fonte: IBGE / SIDRA - PNAD Contínua trimestral e Censo 2022.
# -----------------------------------------------------------------------------

UF_CODIGOS = dict(zip(dados["UF"].astype(str), dados["Código"].astype(int)))
CODIGOS_UF = {str(codigo): sigla for sigla, codigo in UF_CODIGOS.items()}



@st.cache_data(ttl=86400, show_spinner=False)
def consultar_sidra(tabela, variaveis, periodos, classificacoes="", nivel="n3/all"):
    # Converte o nível territorial
    tipo, codigo = nivel.split("/")
    localidade = "BR" if tipo == "n1" else f"N{tipo[1:]}[{codigo}]"

    # Converte as classificações
    classes = []
    if classificacoes:
        partes = classificacoes.strip("/").split("/")
        for i in range(0, len(partes), 2):
            numero = partes[i].replace("c", "", 1)
            classes.append(f"{numero}[{partes[i + 1]}]")

    # Nova API do IBGE
    url = (
        f"https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}"
        f"/periodos/{periodos.replace(',', '|')}"
        f"/variaveis/{variaveis.replace(',', '|')}"
    )

    params = {
        "localidades": localidade,
        "view": "flat"
    }

    if classes:
        params["classificacao"] = "|".join(classes)

    resposta = requests.get(url, params=params, timeout=35)

    if not resposta.ok:
        raise ValueError(
            f"IBGE retornou {resposta.status_code}: "
            f"{resposta.text[:300]}"
        )

    linhas = resposta.json()

    if not isinstance(linhas, list) or len(linhas) < 2:
        raise ValueError("O IBGE não retornou dados suficientes.")

    tabela_df = pd.DataFrame(linhas[1:]).rename(columns=linhas[0])

    tabela_df["Valor"] = pd.to_numeric(
        tabela_df["Valor"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

    return tabela_df.dropna(subset=["Valor"])

    """Consulta o IBGE e devolve uma tabela com valores numéricos."""
    url = (f"https://apisidra.ibge.gov.br/values/t/{tabela}/{nivel}/"
           f"v/{variaveis}/p/{periodos}/")
    if classificacoes:
        url += f"{classificacoes}/"
    url += "?formato=json"
    resposta = requests.get(url, timeout=35, headers={"User-Agent": "DashboardEscolar/1.0"})
    resposta.raise_for_status()
    linhas = resposta.json()
    if not isinstance(linhas, list) or len(linhas) < 2:
        raise ValueError(f"Sem resultados na tabela {tabela} do IBGE.")
    tabela_df = pd.DataFrame(linhas[1:]).rename(columns=linhas[0])
    tabela_df["Valor"] = pd.to_numeric(
        tabela_df["Valor"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
    return tabela_df.dropna(subset=["Valor"])


def encontrar_coluna(df, texto):
    opcoes = [c for c in df.columns if texto.lower() in c.lower() and "(Código)" not in c]
    if not opcoes:
        raise ValueError(f"A coluna '{texto}' não foi encontrada no retorno do IBGE.")
    return opcoes[0]


def normalizar_sidra(df, com_uf=True):
    df = df.copy()
    if com_uf:
        df["UF"] = df["Unidade da Federação (Código)"].astype(str).map(CODIGOS_UF)
        df = df[df["UF"].notna()]
    df["Variavel"] = df["Variável (Código)"].astype(str)
    if "Trimestre (Código)" in df.columns:
        df["Ano"] = df["Trimestre (Código)"].astype(str).str[:4]
    elif "Ano (Código)" in df.columns:
        df["Ano"] = df["Ano (Código)"].astype(str).str[:4]
    return df


# 4. Taxa de desemprego real e número de desocupados, por UF e sexo.
st.subheader("4. Taxa de desemprego real por UF e sexo — 2012 × 2026")
st.caption("PNAD Contínua / IBGE, 1º trimestre de cada ano. Taxa de desocupação = desocupados / força de trabalho.")
trabalho = pd.DataFrame()
try:
    trabalho = normalizar_sidra(consultar_sidra(
        4093, "4099,4092,12466", "201201,202601", "c2/all"
    ))
    trabalho["Sexo"] = trabalho[encontrar_coluna(trabalho, "Sexo")].astype(str).str.strip()
    trabalho = trabalho.pivot_table(
        index=["UF", "Ano", "Sexo"], columns="Variavel", values="Valor", aggfunc="first"
    ).reset_index()
    if not {"4099", "4092"}.issubset(trabalho.columns):
        raise ValueError("A PNAD não devolveu taxa e quantidade de desempregados.")

    taxas = trabalho[trabalho["Sexo"] == sexo].copy()
    if uf != "Todas":
        taxas = taxas[taxas["UF"] == uf]
    graf_taxa = px.bar(
        taxas, x="UF", y="4099", color="Ano", barmode="group",
        labels={"4099": "Taxa de desemprego (%)", "UF": "Estado"},
        color_discrete_sequence=["#377db4", "#f59e0b"],
    )
    st.plotly_chart(graf_taxa, use_container_width=True)

    st.caption("Comparação de homens e mulheres nos dois anos:")
    generos = trabalho[trabalho["Sexo"].isin(["Homens", "Mulheres"])].copy()
    if uf != "Todas":
        generos = generos[generos["UF"] == uf]
    graf_sexo = px.bar(
        generos, x="UF", y="4099", color="Sexo", facet_col="Ano", barmode="group",
        labels={"4099": "Taxa de desemprego (%)", "UF": "Estado"},
        color_discrete_sequence=["#377db4", "#e879a5"],
    )
    st.plotly_chart(graf_sexo, use_container_width=True)
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar as taxas de desemprego no IBGE: {erro}")

# 5. Identifica o estado que mais reduziu a quantidade de pessoas desocupadas.
st.subheader("5. Qual estado mais reduziu a população desempregada?")
if not trabalho.empty and "4092" in trabalho.columns:
    quantidade = trabalho[trabalho["Sexo"] == "Total"][["UF", "Ano", "4092"]].copy()
    # Se a categoria Total não vier, usa a soma de homens e mulheres por UF/ano.
    if quantidade.empty:
        quantidade = (trabalho[trabalho["Sexo"].isin(["Homens", "Mulheres"])]
                      .groupby(["UF", "Ano"], as_index=False)["4092"].sum())
    quantidade = quantidade.pivot_table(
        index="UF", columns="Ano", values="4092", aggfunc="first"
    ).reindex(columns=["2012", "2026"]).dropna(subset=["2012", "2026"])

    if not quantidade.empty:
        quantidade["Variação (mil pessoas)"] = quantidade["2026"] - quantidade["2012"]
        quedas = quantidade[quantidade["Variação (mil pessoas)"] < 0]
        if not quedas.empty:
            vencedor = quedas["Variação (mil pessoas)"].idxmin()
            reducao = abs(quedas.loc[vencedor, "Variação (mil pessoas)"])
            st.success(f"Maior redução: **{vencedor}**, cerca de **{reducao:,.0f} mil pessoas** a menos.")
        else:
            st.info("Nenhum estado apresentou redução na quantidade estimada de desocupados.")
        tabela_reducao = quantidade if uf == "Todas" else quantidade[quantidade.index == uf]
        st.dataframe(tabela_reducao.reset_index().round(1), use_container_width=True, hide_index=True)
        st.caption("Unidade: mil pessoas. A classificação de maior redução considera todas as UFs, mesmo quando há filtro de estado.")
    else:
        st.info("O IBGE não devolveu dados completos dos dois anos para calcular a redução.")
else:
    st.info("A comparação da quantidade depende da consulta à PNAD, exibida na seção anterior.")

# 6. Formalidade x informalidade: complemento da taxa de informalidade do IBGE.
st.subheader("6. Formalidade × informalidade — barras agrupadas")
if not trabalho.empty and "12466" in trabalho.columns:
    informal = trabalho[(trabalho["Ano"] == str(ano_grafico)) &
                       (trabalho["Sexo"] == sexo)].copy()
    if uf != "Todas":
        informal = informal[informal["UF"] == uf]
    informal = informal.dropna(subset=["12466"])
    if not informal.empty:
        informal["Informal"] = informal["12466"]
        informal["Formal"] = 100 - informal["Informal"]
        graf_formal = informal.melt(
            id_vars="UF", value_vars=["Formal", "Informal"],
            var_name="Situação", value_name="Percentual",
        )
        fig_formal = px.bar(
            graf_formal, x="UF", y="Percentual", color="Situação", barmode="group",
            labels={"Percentual": "Pessoas ocupadas (%)"},
            color_discrete_sequence=["#16a34a", "#f97316"],
        )
        fig_formal.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(fig_formal, use_container_width=True)
        st.caption(f"PNAD, 1º trimestre de {ano_grafico}. Formal = complemento da taxa de informalidade, não apenas carteira assinada.")
    else:
        st.info(f"A taxa de informalidade não está disponível para {ano_grafico} nesse recorte. Tente 2026.")
else:
    st.info("A taxa de informalidade depende da consulta ao IBGE.")

# 7. Emprego por setor econômico: gráfico utiliza apenas dados existentes da PNAD.
st.subheader("7. Pessoas ocupadas por setor econômico")
st.caption("PNAD 2026. 'Agro', 'Indústria' e 'Serviços' são grupos de atividades, não taxas de desemprego.")
try:
    atividade = normalizar_sidra(consultar_sidra(5434, "4090", "202601", "c888/all"))
    atividade["Atividade"] = atividade[encontrar_coluna(atividade, "Grupamentos de atividades")].astype(str)

    def classificar_setor(nome):
        texto = nome.lower()
        if texto == "total" or "indústria de transformação" in texto or "mal definidas" in texto:
            return None  # Exclui total e subdivisões que poderiam duplicar contagens.
        if "agricultura" in texto or "pecuária" in texto:
            return "Agro"
        if "indústria geral" in texto or "construção" in texto:
            return "Indústria"
        return "Serviços"

    atividade["Setor"] = atividade["Atividade"].apply(classificar_setor)
    atividade = atividade[atividade["Setor"].notna()]
    if setor != "Todos":
        atividade = atividade[atividade["Setor"] == setor]
    if uf != "Todas":
        atividade = atividade[atividade["UF"] == uf]
    por_setor = atividade.groupby(["UF", "Setor"], as_index=False)["Valor"].sum()
    if por_setor.empty:
        st.info("Sem dados do setor selecionado.")
    else:
        fig_setor = px.bar(
            por_setor, x="UF", y="Valor", color="Setor", barmode="group",
            labels={"Valor": "Pessoas ocupadas (mil)", "UF": "Estado"},
        )
        st.plotly_chart(fig_setor, use_container_width=True)
    st.caption("Este gráfico aplica os filtros de UF e Setor, mas não os de Sexo e Escolaridade.")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar os setores econômicos: {erro}")

# 8. Escolaridade: taxa por nível de instrução em 2012 e 2026.
st.subheader("8. Desemprego por escolaridade — 2012 × 2026")
try:
    educacao = normalizar_sidra(consultar_sidra(4095, "4099", "201201,202601", "c1568/all"))
    educacao["Escolaridade"] = educacao[encontrar_coluna(educacao, "Nível de instrução")].astype(str)
    if escolaridade == "Todas":
        educacao = educacao[educacao["Escolaridade"] == "Total"]
    else:
        educacao = educacao[educacao["Escolaridade"] == escolaridade]
    if uf != "Todas":
        educacao = educacao[educacao["UF"] == uf]
    if educacao.empty:
        st.info("Sem dados para a escolaridade selecionada.")
    else:
        fig_edu = px.bar(
            educacao, x="UF", y="Valor", color="Ano", barmode="group",
            labels={"Valor": "Taxa de desemprego (%)", "UF": "Estado"},
            color_discrete_sequence=["#377db4", "#f59e0b"],
        )
        st.plotly_chart(fig_edu, use_container_width=True)
    st.caption("Filtro de escolaridade aplicado. A tabela da PNAD consultada não permite cruzá-lo com o filtro de Sexo.")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar a escolaridade: {erro}")

# 9. Histograma de faixas de rendimento, junto da média e mediana.
# O Censo 2022 é uma fonte extra apenas para rendimentos; não substitui a PNAD 2012/2026.
st.subheader("9. Histograma de rendimento do trabalho, média e mediana")
st.caption("Fonte: Censo Demográfico 2022 (IBGE). Esta seção usa 2022 porque as planilhas de 2012 e 2026 não trazem rendimentos.")
nivel = "n1/all" if uf == "Todas" else f"n3/{UF_CODIGOS[uf]}"
FAIXAS_RENDA = [
    "Sem rendimento", "Até 1/4 de salário mínimo",
    "Mais de 1/4 a 1/2 salário mínimo", "Mais de 1/2 a 1 salário mínimo",
    "Mais de 1 a 2 salários mínimos", "Mais de 2 a 3 salários mínimos",
    "Mais de 3 a 5 salários mínimos", "Mais de 5 a 10 salários mínimos",
    "Mais de 10 a 15 salários mínimos", "Mais de 15 a 20 salários mínimos",
    "Mais de 20 salários mínimos",
]
try:
    renda = normalizar_sidra(consultar_sidra(
        10292, "13600", "2022", "c2/all/c11915/all", nivel
    ), com_uf=False)
    renda["Sexo"] = renda[encontrar_coluna(renda, "Sexo")].astype(str).str.strip()
    renda["Faixa"] = renda[encontrar_coluna(renda, "Classes de rendimento")].astype(str).str.strip()
    renda = renda[(renda["Sexo"] == sexo) & (renda["Faixa"].isin(FAIXAS_RENDA))]
    if renda.empty:
        st.info("Não foram encontradas faixas de rendimento para este recorte.")
    else:
        renda["Faixa"] = pd.Categorical(renda["Faixa"], categories=FAIXAS_RENDA, ordered=True)
        renda = renda.sort_values("Faixa")
        fig_renda = px.bar(
            renda, x="Faixa", y="Valor",
            labels={"Valor": "Trabalhadores (%)", "Faixa": "Faixa de rendimento"},
            color_discrete_sequence=["#377db4"],
        )
        fig_renda.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig_renda, use_container_width=True)
        st.caption("Histograma por faixas (dados agrupados). Não representa salários individuais.")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar as faixas salariais: {erro}")

# Média e mediana do trabalho por sexo, escolaridade e seção econômica do Censo.
try:
    res = normalizar_sidra(consultar_sidra(
        10284, "13536,13537", "2022", "c2/all/c1568/all/c11805/all", nivel
    ), com_uf=False)
    res["Sexo"] = res[encontrar_coluna(res, "Sexo")].astype(str).str.strip()
    res["Escolaridade"] = res[encontrar_coluna(res, "Nível de instrução")].astype(str).str.strip()
    res["Atividade"] = res[encontrar_coluna(res, "Seção de atividade")].astype(str).str.strip()
    res_todos = res.copy()
    # Mostra médias/medianas sem cruzamentos quando o usuário está em "Todos".
    res = res[(res["Sexo"] == sexo) & (res["Escolaridade"] == "Total") &
              (res["Atividade"] == "Total")]
    medidas = dict(zip(res["Variavel"], res["Valor"]))
    if {"13536", "13537"}.issubset(medidas):
        media, mediana = medidas["13536"], medidas["13537"]
        m1, m2 = st.columns(2)
        m1.metric("Média mensal", f"R$ {media:,.0f}")
        m2.metric("Mediana mensal", f"R$ {mediana:,.0f}")
        if media > mediana:
            st.info("A média supera a mediana: os rendimentos altos aumentam a média, mostrando assimetria à direita.")
        elif media < mediana:
            st.info("A média está abaixo da mediana, indicando assimetria à esquerda.")
        else:
            st.info("Média e mediana são semelhantes neste recorte.")
    else:
        st.info("Média e mediana não disponíveis neste recorte.")
    st.caption("O histograma e as medidas acima respondem a UF e Sexo; Setor e Escolaridade são aplicados na comparação salarial abaixo.")

    st.subheader("Paridade salarial: homens × mulheres (Censo 2022)")
    # O Censo agrupa a escolaridade em faixas mais largas que a PNAD.
    escola_censo = {
        "Todas": "Total",
        "Sem instrução e menos de 1 ano de estudo": "Sem instrução e fundamental incompleto",
        "Ensino fundamental incompleto ou equivalente": "Sem instrução e fundamental incompleto",
        "Ensino fundamental completo ou equivalente": "Fundamental completo e médio incompleto",
        "Ensino médio incompleto ou equivalente": "Fundamental completo e médio incompleto",
        "Ensino médio completo ou equivalente": "Médio completo e superior incompleto",
        "Ensino superior incompleto ou equivalente": "Médio completo e superior incompleto",
        "Ensino superior completo ou equivalente": "Superior completo",
    }

    def classificar_setor_censo(nome):
        atividade = nome.lower()
        if atividade == "total":
            return "Todos"
        if "agricultura" in atividade or "pecuária" in atividade:
            return "Agro"
        if any(p in atividade for p in ["indústria", "indústrias", "construção",
                                        "eletricidade", "água, esgoto"]):
            return "Indústria"
        return "Serviços"

    paridade = res_todos[
        (res_todos["Sexo"].isin(["Homens", "Mulheres"])) &
        (res_todos["Escolaridade"] == escola_censo[escolaridade])
    ].copy()
    paridade["Setor"] = paridade["Atividade"].apply(classificar_setor_censo)
    if setor == "Todos":
        paridade = paridade[paridade["Atividade"] == "Total"]
    else:
        paridade = paridade[paridade["Setor"] == setor]
    paridade["Indicador"] = paridade["Variavel"].map({"13536": "Média", "13537": "Mediana"})
    paridade = paridade[paridade["Indicador"].notna()]
    if paridade.empty:
        st.info("Sem rendimentos disponíveis para essa combinação de filtros.")
    else:
        fig_paridade = px.bar(
            paridade, x="Sexo" if setor == "Todos" else "Atividade", y="Valor",
            color="Sexo", facet_row="Indicador", barmode="group",
            labels={"Valor": "Rendimento mensal (R$)", "Atividade": "Ramo de trabalho"},
            color_discrete_sequence=["#377db4", "#e879a5"],
        )
        fig_paridade.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig_paridade, use_container_width=True)
        st.dataframe(paridade[["Sexo", "Escolaridade", "Atividade", "Indicador", "Valor"]].round(0),
                     use_container_width=True, hide_index=True)
    st.caption("Esta comparação mostra diferenças observadas, não prova discriminação por trabalho equivalente. "
               "O Censo utiliza grupos escolares mais amplos e não se deve somar médias ou medianas de ramos diferentes.")
except (requests.RequestException, ValueError, KeyError) as erro:
    st.warning(f"Não foi possível carregar média e mediana: {erro}")

st.subheader("10. Ideias para a mesa de negociação")
st.write("**Márcia (Governo):** ampliar a qualificação e a fiscalização do trabalho formal.")
st.write("**Renato (Indústria):** estimular contratações e investir em capacitação profissional.")
st.write("**Sílvia (Sebrae):** ajudar pequenos negócios na formalização e incentivar transparência salarial.")

# Conteúdo original: notícias e fotos.
st.subheader("📰 Notícias sobre emprego")
st.markdown(
    "- **PNAD Contínua (IBGE, 2º trimestre de 2026):** "
    "[taxa de desocupação de 5,4% no Brasil](https://www.gov.br/secom/pt-br/acompanhe-a-secom/noticias/2026/07/ibge-divulga-resultados-da-pnad-continua-referentes-ao-trimestre-encerrado-em-junho-de-2026/).\n"
    "- **Novo Caged (4 de novembro de 2026):** "
    "[121,3 mil vagas formais geradas em setembro](https://agenciagov.ebc.com.br/noticias/202611/brasil-gera-121-3-mil-empregos-formais-em-setembro-e-saldo-no-ano-chega-a-1-24-milhao-de-novos-postos-com-carteira-assinada)."
)

st.subheader("📷 Trabalhadores brasileiros")
c1, c2 = st.columns(2)
with c1:
    st.image(
        "https://commons.wikimedia.org/wiki/Special:FilePath/Fabrica_Farinha_Acari.jpg?width=800",
        caption="Fábrica de farinha, Acari (RN). Casteliane / Wikimedia Commons (CC BY-SA 3.0).",
        use_container_width=True,
    )
with c2:
    st.image(
        "https://commons.wikimedia.org/wiki/Special:FilePath/Agricultura_familiar_(15643548663).jpg?width=800",
        caption="Agricultura familiar, Bahia. Sergio Amaral / MDS / Wikimedia Commons (CC BY-SA 2.0).",
        use_container_width=True,
    )

st.divider()
st.caption(
    "Fontes oficiais: "
    "[PNAD 4093](https://sidra.ibge.gov.br/tabela/4093) · "
    "[PNAD 4095](https://sidra.ibge.gov.br/tabela/4095) · "
    "[PNAD 5434](https://sidra.ibge.gov.br/tabela/5434) · "
    "[Censo 10292](https://sidra.ibge.gov.br/tabela/10292) · "
    "[Censo 10284](https://sidra.ibge.gov.br/tabela/10284). "
    "PNAD (2012/2026) e Censo (2022) são bases diferentes."
)
