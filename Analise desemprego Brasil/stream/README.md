# Dashboard básico — Trabalho e População Desocupada

## Como executar

1. Abra a pasta no VS Code.
2. No terminal, execute:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## O que o dashboard mostra

- Filtro por UF e sexo.
- Comparação de 2012 e 2026 por UF.
- Gráfico empilhado de homens e mulheres desocupados.
- Tabela de variações em pontos percentuais.
- Links de notícias e fotos de trabalhadores brasileiros.

## Importante para a apresentação

Os arquivos trazem a distribuição percentual dos desocupados por sexo em cada UF, e **não** a taxa de desocupação. Os percentuais de homens e mulheres somam aproximadamente 100% em cada estado. Por isso, não é correto afirmar que esses percentuais indicam a taxa geral de desemprego ou o número de desempregados.

O enunciado pediu **2012 e 2022**, mas o segundo arquivo enviado é de **2026**. O dashboard usa apenas 2012 e 2026.

Não foram fornecidos dados sobre setor econômico, escolaridade, formalidade/informalidade ou rendimentos. Os filtros correspondentes aparecem desabilitados, e os dois gráficos exigidos para esses temas estão sinalizados como indisponíveis. Se a escola disponibilizar planilhas específicas, eles podem ser acrescentados depois.

## Sugestão de fala na apresentação

"Somos uma startup de análise de dados. Nosso painel ajuda a comparar como homens e mulheres representam a população desocupada nos estados em 2012 e 2026. As diferenças são apresentadas em pontos percentuais. Para definir políticas de redução do desemprego, precisamos complementar esses dados com as taxas de desocupação, formalidade e salários."

## Fontes dos materiais extras

- PNAD Contínua: https://www.gov.br/secom/pt-br/acompanhe-a-secom/noticias/2026/07/ibge-divulga-resultados-da-pnad-continua-referentes-ao-trimestre-encerrado-em-junho-de-2026/
- Novo Caged (04/11/2026): https://agenciagov.ebc.com.br/noticias/202611/brasil-gera-121-3-mil-empregos-formais-em-setembro-e-saldo-no-ano-chega-a-1-24-milhao-de-novos-postos-com-carteira-assinada
- Fotografia fábrica: https://commons.wikimedia.org/wiki/File:Fabrica_Farinha_Acari.jpg — Casteliane (CC BY-SA 3.0)
- Fotografia agricultura: https://commons.wikimedia.org/wiki/File:Agricultura_familiar_(15643548663).jpg — Sergio Amaral / MDS (CC BY-SA 2.0)
