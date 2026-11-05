import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Trabalho e Desocupação", layout="wide")
st.title("📊 Trabalho e População Desocupada")
st.write("Comparação entre o 1º trimestre de 2012 e o 1º trimestre de 2026, por estado e sexo.")


@st.cache_data
def carregar_dados():
    df_2012 = pd.read_excel("Tabela5-sem_emprego_2012.xlsx", engine="calamine")
    df_2026 = pd.read_excel("Tabela5-sem_emprego_2026.xlsx", engine="calamine")

    # As colunas 4 e 5 apresentam a distribuição dos desocupados por sexo.
    for df, ano in [(df_2012, 2012), (df_2026, 2026)]:
        df.columns = ["UF", "Código", "Estado", "Homens", "Mulheres"]
        df["Ano"] = ano

    return pd.concat([df_2012, df_2026], ignore_index=True)


dados = carregar_dados()

st.sidebar.header("Filtros")
uf = st.sidebar.selectbox("UF", ["Todas"] + sorted(dados["UF"].unique().tolist()))
sexo = st.sidebar.selectbox("Sexo", ["Homens", "Mulheres"])
ano_grafico = st.sidebar.selectbox("Ano para o 2º gráfico", [2012, 2026], index=1)
st.sidebar.selectbox("Setor econômico", ["Sem dados"], disabled=True)
st.sidebar.selectbox("Escolaridade", ["Sem dados"], disabled=True)
st.sidebar.caption("As planilhas não têm setor econômico nem escolaridade.")

filtrado = dados if uf == "Todas" else dados[dados["UF"] == uf]

st.info(
    "Atenção: estes percentuais mostram a **participação de homens e mulheres "
    "entre as pessoas desocupadas**, não a taxa de desemprego da população."
)

col1, col2 = st.columns(2)
col1.metric("UFs selecionadas", filtrado["UF"].nunique())
col2.metric("Anos comparados", "2012 e 2026")

# Gráfico 1: comparação da participação do sexo escolhido entre os anos.
st.subheader(f"1. Comparação entre 2012 e 2026 — {sexo}")
fig1 = px.bar(
    filtrado.assign(Ano=filtrado["Ano"].astype(str)),
    x="UF",
    y=sexo,
    color="Ano",
    barmode="group",
    color_discrete_sequence=["#377db4", "#f59e0b"],
    labels={sexo: "Participação entre desocupados (%)", "UF": "Estado", "Ano": "Ano"},
    hover_data=["Estado"],
)
fig1.update_layout(yaxis_range=[0, 100])
st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2: participação masculina e feminina no ano escolhido.
st.subheader(f"2. Distribuição dos desocupados por sexo — {ano_grafico}")
so_ano = filtrado[filtrado["Ano"] == ano_grafico]
fig2 = px.bar(
    so_ano,
    x="UF",
    y=["Homens", "Mulheres"],
    barmode="stack",
    labels={"value": "Participação (%)", "variable": "Sexo", "UF": "Estado"},
    color_discrete_sequence=["#377db4", "#e879a5"],
)
fig2.update_layout(yaxis_range=[0, 100])
st.plotly_chart(fig2, use_container_width=True)

# Tabela de diferenças: pontos percentuais, NÃO redução do nº de desempregados.
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
        f"**Maior queda na participação masculina entre os desocupados:** "
        f"{menor_h['Estado']} ({menor_h['Mudança homens (p.p.)']:+.1f} ponto(s) percentual(is))."
    )

st.warning(
    "Não é possível determinar qual estado mais reduziu o número de desempregados, "
    "nem criar os gráficos de formalidade/informalidade ou de rendimentos: "
    "essas informações não aparecem nos arquivos enviados."
)

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
st.caption("As fotos são carregadas da internet. Fontes: Wikimedia Commons.")
