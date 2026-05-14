import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta
import calendar

DATABASE_URL = os.environ.get("DATABASE_URL")

VALOR_POR_PACOTE = 2.00
BONUS_POR_PACOTE = 0.30
META_TAXA = 98.0


def conectar():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def criar_banco():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entregas (
            id SERIAL PRIMARY KEY,
            data TEXT UNIQUE NOT NULL,
            recebidos INTEGER NOT NULL,
            entregues INTEGER NOT NULL,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pacotes_ids (
            id SERIAL PRIMARY KEY,
            data TEXT NOT NULL,
            codigo TEXT UNIQUE NOT NULL,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS historico_alteracoes (
            id SERIAL PRIMARY KEY,
            acao TEXT NOT NULL,
            descricao TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def salvar_entrega(data, recebidos, entregues):
    conn = conectar()
    cur = conn.cursor()

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO entregas (data, recebidos, entregues, criado_em)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (data) DO UPDATE SET
            recebidos = EXCLUDED.recebidos,
            entregues = EXCLUDED.entregues,
            criado_em = EXCLUDED.criado_em
    """, (data, recebidos, entregues, agora))

    conn.commit()
    cur.close()
    conn.close()


def salvar_ids_pacotes(data, ids):
    conn = conectar()
    cur = conn.cursor()

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    erros = []

    for codigo in ids:
        codigo = codigo.strip()

        if not codigo:
            continue

        try:
            cur.execute("""
                INSERT INTO pacotes_ids (data, codigo, criado_em)
                VALUES (%s, %s, %s)
            """, (data, codigo, agora))
        except Exception:
            conn.rollback()
            erros.append(codigo)

    conn.commit()
    cur.close()
    conn.close()

    return erros


def listar_ids_por_data(data):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM pacotes_ids
        WHERE data = %s
        ORDER BY id DESC
    """, (data,))

    dados = cur.fetchall()
    cur.close()
    conn.close()

    return dados


def total_ids_data(data):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM pacotes_ids
        WHERE data = %s
    """, (data,))

    total = cur.fetchone()["total"]

    cur.close()
    conn.close()

    return total


def buscar_id_pacote(codigo):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM pacotes_ids
        WHERE codigo ILIKE %s
        ORDER BY data DESC
    """, (f"%{codigo}%",))

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return dados


def registrar_historico(acao, descricao):
    conn = conectar()
    cur = conn.cursor()

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO historico_alteracoes (acao, descricao, data_hora)
        VALUES (%s, %s, %s)
    """, (acao, descricao, agora))

    conn.commit()
    cur.close()
    conn.close()


def listar_historico(limite=100):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM historico_alteracoes
        ORDER BY id DESC
        LIMIT %s
    """, (limite,))

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return dados


def listar_ultimos_registros(limite=10):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM entregas
        ORDER BY data DESC
        LIMIT %s
    """, (limite,))

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return dados


def buscar_por_periodo(inicio, fim):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM entregas
        WHERE data BETWEEN %s AND %s
        ORDER BY data ASC
    """, (inicio, fim))

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return dados


def calcular_totais(registros, aplicar_bonus_mensal=False, taxa_mensal=0):
    recebidos = sum(int(r["recebidos"]) for r in registros)
    entregues = sum(int(r["entregues"]) for r in registros)

    taxa = (entregues / recebidos * 100) if recebidos > 0 else 0
    valor_normal = entregues * VALOR_POR_PACOTE

    bonus = 0
    if aplicar_bonus_mensal and taxa_mensal > META_TAXA:
        bonus = entregues * BONUS_POR_PACOTE

    total = valor_normal + bonus

    return {
        "recebidos": recebidos,
        "entregues": entregues,
        "taxa": taxa,
        "valor_normal": valor_normal,
        "bonus": bonus,
        "total": total
    }


def hoje_str():
    return date.today().strftime("%Y-%m-%d")


def inicio_semana():
    hoje = date.today()
    inicio = hoje - timedelta(days=hoje.weekday())
    return inicio.strftime("%Y-%m-%d")


def fim_semana():
    hoje = date.today()
    fim = hoje + timedelta(days=(6 - hoje.weekday()))
    return fim.strftime("%Y-%m-%d")


def inicio_mes():
    hoje = date.today()
    return date(hoje.year, hoje.month, 1).strftime("%Y-%m-%d")


def fim_mes():
    hoje = date.today()
    ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
    return date(hoje.year, hoje.month, ultimo).strftime("%Y-%m-%d")


def inicio_quinzena():
    hoje = date.today()
    if hoje.day <= 15:
        return date(hoje.year, hoje.month, 1).strftime("%Y-%m-%d")
    return date(hoje.year, hoje.month, 16).strftime("%Y-%m-%d")


def fim_quinzena():
    hoje = date.today()
    if hoje.day <= 15:
        return date(hoje.year, hoje.month, 15).strftime("%Y-%m-%d")

    ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
    return date(hoje.year, hoje.month, ultimo).strftime("%Y-%m-%d")


def dados_grafico_mes():
    registros = buscar_por_periodo(inicio_mes(), fim_mes())

    labels = []
    recebidos = []
    entregues = []

    for r in registros:
        labels.append(r["data"])
        recebidos.append(r["recebidos"])
        entregues.append(r["entregues"])

    return {
        "labels": labels,
        "recebidos": recebidos,
        "entregues": entregues
    }


def dados_dashboard():
    hoje = hoje_str()

    registros_hoje = buscar_por_periodo(hoje, hoje)
    registros_semana = buscar_por_periodo(inicio_semana(), fim_semana())
    registros_quinzena = buscar_por_periodo(inicio_quinzena(), fim_quinzena())
    registros_mes = buscar_por_periodo(inicio_mes(), fim_mes())

    mensal_sem_bonus = calcular_totais(registros_mes)
    taxa_mensal = mensal_sem_bonus["taxa"]

    return {
        "hoje": calcular_totais(registros_hoje),
        "semana": calcular_totais(registros_semana),
        "quinzena": calcular_totais(registros_quinzena),
        "mes": calcular_totais(registros_mes, True, taxa_mensal),
        "taxa_mensal": taxa_mensal,
        "ultimos": listar_ultimos_registros(8),
        "grafico": dados_grafico_mes(),
        "meta_batida": taxa_mensal > META_TAXA
    }


def nome_periodo(periodo):
    nomes = {
        "hoje": "Hoje",
        "semana": "Semana atual",
        "quinzena": "Quinzena atual",
        "mes": "Mês atual",
        "personalizado": "Personalizado"
    }

    return nomes.get(periodo, "Mês atual")


def datas_por_periodo(periodo, inicio=None, fim=None):
    if periodo == "hoje":
        d = hoje_str()
        return d, d

    if periodo == "semana":
        return inicio_semana(), fim_semana()

    if periodo == "quinzena":
        return inicio_quinzena(), fim_quinzena()

    if periodo == "personalizado" and inicio and fim:
        return inicio, fim

    return inicio_mes(), fim_mes()


def dados_relatorio(periodo="mes", inicio=None, fim=None):
    data_inicio, data_fim = datas_por_periodo(periodo, inicio, fim)
    registros = buscar_por_periodo(data_inicio, data_fim)

    totais_sem_bonus = calcular_totais(registros)
    taxa = totais_sem_bonus["taxa"]
    totais = calcular_totais(registros, True, taxa)

    linhas = []

    for r in registros:
        recebidos = int(r["recebidos"])
        entregues = int(r["entregues"])

        taxa_dia = (entregues / recebidos * 100) if recebidos > 0 else 0
        valor = entregues * VALOR_POR_PACOTE

        linhas.append({
            "data": r["data"],
            "recebidos": recebidos,
            "entregues": entregues,
            "taxa": taxa_dia,
            "valor": valor
        })

    return {
        "periodo": periodo,
        "nome_periodo": nome_periodo(periodo),
        "inicio": data_inicio,
        "fim": data_fim,
        "totais": totais,
        "linhas": linhas
    }