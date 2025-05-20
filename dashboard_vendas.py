# -*- coding: utf-8 -*-
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Leitura e preparo dos dados
vendas_2020 = pd.read_excel("Base Vendas - 2020.xlsx")
vendas_2021 = pd.read_excel("Base Vendas - 2021.xlsx")
vendas_2022 = pd.read_excel("Base Vendas - 2022.xlsx")
colunas_padrao = ["Data da Venda", "Ordem de Compra", "ID Produto", "ID Cliente", "Qtd Vendida", "ID Loja"]
vendas_2020.columns = colunas_padrao
vendas_2021.columns = colunas_padrao
vendas_2022.columns = colunas_padrao
vendas = pd.concat([vendas_2020, vendas_2021, vendas_2022], ignore_index=True)

produtos = pd.read_excel("Cadastro Produtos.xlsx")
lojas = pd.read_excel("Cadastro Lojas.xlsx")

produtos.rename(columns={'SKU': 'ID Produto'}, inplace=True)
vendas["Data da Venda"] = pd.to_datetime(vendas["Data da Venda"], dayfirst=True)

base = vendas.merge(produtos, on="ID Produto", how="left")
base = base.merge(lojas, on="ID Loja", how="left")
base["Ano"] = base["Data da Venda"].dt.year
base["Valor da Venda"] = base["Qtd Vendida"] * base["Preço Unitario"]

filtros = {
    "produto": base["Produto"].dropna().unique(),
    "loja": base["Nome da Loja"].dropna().unique(),
    "marca": base["Marca"].dropna().unique(),
    "tipo": base["Tipo do Produto"].dropna().unique(),
}

app = dash.Dash(__name__)
server = app.server

app.layout = dbc.Container([
    html.H1("📈 Análises Alternativas de Vendas", className="text-center my-4"),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='filtro_tipo', options=[{'label': i, 'value': i} for i in filtros['tipo']],
                             placeholder="Selecione o Tipo de Produto"), md=4),
        dbc.Col(dcc.Dropdown(id='filtro_marca', placeholder="Selecione a Marca"), md=4),
        dbc.Col(dcc.Dropdown(id='filtro_loja', options=[{'label': i, 'value': i} for i in filtros['loja']],
                             multi=True, placeholder="Filtrar por Loja"), md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico_variacao_anual'), md=6),
        dbc.Col(dcc.Graph(id='grafico_qtd_tipo'), md=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico_pizza_marca'), md=6),
        dbc.Col(dcc.Graph(id='grafico_ticket_medio_loja'), md=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico_bolha_produtos'), md=6),
        dbc.Col(dcc.Graph(id='grafico_frequencia_clientes'), md=6),
    ])
], fluid=True)

@app.callback(
    Output('filtro_marca', 'options'),
    Input('filtro_tipo', 'value')
)
def atualizar_marcas(tipo):
    if tipo:
        marcas = base[base['Tipo do Produto'] == tipo]['Marca'].dropna().unique()
        return [{'label': m, 'value': m} for m in marcas]
    return []

@app.callback(
    [Output('grafico_variacao_anual', 'figure'),
     Output('grafico_qtd_tipo', 'figure'),
     Output('grafico_pizza_marca', 'figure'),
     Output('grafico_ticket_medio_loja', 'figure'),
     Output('grafico_bolha_produtos', 'figure'),
     Output('grafico_frequencia_clientes', 'figure')],
    [Input('filtro_tipo', 'value'),
     Input('filtro_marca', 'value'),
     Input('filtro_loja', 'value')]
)
def atualizar_graficos(tipo, marca, lojas):
    df = base.copy()
    if tipo:
        df = df[df['Tipo do Produto'] == tipo]
    if marca:
        df = df[df['Marca'] == marca]
    if lojas:
        df = df[df['Nome da Loja'].isin(lojas)]

    vendas_ano = df.groupby("Ano")["Valor da Venda"].sum().pct_change().fillna(0).reset_index()
    vendas_ano["Variação (%)"] = vendas_ano["Valor da Venda"] * 100

    fig1 = px.line(vendas_ano, x="Ano", y="Variação (%)",
                   title="Variação Percentual de Vendas por Ano", markers=True,
                   template='plotly_white')

    fig2 = px.bar(df.groupby("Tipo do Produto")["Qtd Vendida"].sum().reset_index(),
                  x="Tipo do Produto", y="Qtd Vendida", title="Quantidade Vendida por Tipo de Produto",
                  color_discrete_sequence=["#20B2AA"], template='plotly_white')

    fig3 = px.pie(df, names="Marca", values="Valor da Venda", title="Distribuição por Marca",
                  template='plotly_white')

    ticket = df.groupby("Nome da Loja").apply(lambda x: x["Valor da Venda"].sum() / x["ID Cliente"].nunique()).reset_index(name="Ticket Médio")
    fig4 = px.bar(ticket, x="Ticket Médio", y="Nome da Loja", orientation='h',
                  title="Ticket Médio por Loja", template='plotly_white')

    qtd_prod = df.groupby("Produto")[["Qtd Vendida", "Valor da Venda"]].sum().nlargest(10, "Qtd Vendida").reset_index()
    fig5 = px.scatter(qtd_prod, x="Qtd Vendida", y="Valor da Venda", size="Qtd Vendida", color="Produto",
                      title="Top 10 Produtos por Quantidade Vendida", template='plotly_white')

    clientes = df.groupby("ID Cliente").size().nlargest(10).reset_index(name="Compras")
    fig6 = px.bar(clientes, x="ID Cliente", y="Compras", title="Top 10 Clientes por Frequência de Compra",
                  template='plotly_white', color_discrete_sequence=["#A52A2A"])

    return fig1, fig2, fig3, fig4, fig5, fig6

if __name__ == '__main__':
    app.run_server(debug=True)
