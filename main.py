import os
import sqlite3
import csv
from datetime import datetime

# --- CONFIGURAÇÃO DO BANCO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "banco_dados.db")

def conectar():
    return sqlite3.connect(DB_PATH)

def inicializar_banco():
    """Garante que todas as tabelas existam ao iniciar o programa"""
    conn = conectar()
    cursor = conn.cursor()
    
    # Tabela Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            endereco TEXT
        )
    """)
    # Tabela Produtos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            tamanho TEXT
        )
    """)
    # Tabela Pedidos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            id_cliente INTEGER NOT NULL,
            valor_total REAL NOT NULL,
            FOREIGN KEY (id_cliente) REFERENCES Clientes (id)
        )
    """)
    # Tabela Pedidos_Itens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pedidos_Itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER NOT NULL,
            id_produto INTEGER NOT NULL,
            valor_unitario REAL NOT NULL,
            quantidade INTEGER NOT NULL,
            total REAL NOT NULL,
            FOREIGN KEY (id_pedido) REFERENCES Pedidos (id),
            FOREIGN KEY (id_produto) REFERENCES Produtos (id)
        )
    """)
    conn.commit()
    conn.close()

# --- FUNÇÕES DE CADASTRO ---

def cadastrar_cliente():
    print("\n--- NOVO CLIENTE ---")
    nome = input("Nome: ")
    telefone = input("Telefone: ")
    endereco = input("Endereço: ") # Agora pedimos o endereço!
    
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Clientes (nome, telefone, endereco) VALUES (?, ?, ?)", 
                   (nome, telefone, endereco))
    conn.commit()
    conn.close()
    print(f"✅ Cliente {nome} cadastrado!")

def cadastrar_produto():
    print("\n--- NOVO PRODUTO ---")
    nome = input("Nome do Bolo: ")
    preco = float(input("Preço (ex: 45.50): "))
    tamanho = input("Tamanho: ")
    
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Produtos (nome, preco, tamanho) VALUES (?, ?, ?)", 
                   (nome, preco, tamanho))
    conn.commit()
    conn.close()
    print(f"✅ Produto {nome} cadastrado!")

def ver_cardapio():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Produtos")
    produtos = cursor.fetchall()
    conn.close()
    
    print("\n--- CARDÁPIO ---")
    for p in produtos:
        print(f"ID: {p[0]} | {p[1]} ({p[3]}) - R$ {p[2]:.2f}")
    print("----------------")

# --- FUNÇÃO DE VENDA ---

def nova_venda():
    conn = conectar()
    cursor = conn.cursor()
def relatorio_vendas():
    conn = conectar()
    cursor = conn.cursor()
    
    # O comando JOIN abaixo é o segredo. Ele busca o NOME na tabela Clientes
    # usando o ID que estava gravado na tabela Pedidos.
    sql = """
    SELECT Pedidos.id, Pedidos.data, Clientes.nome, Pedidos.valor_total
    FROM Pedidos
    JOIN Clientes ON Pedidos.id_cliente = Clientes.id
    ORDER BY Pedidos.id DESC
    """
    cursor.execute(sql)
    vendas = cursor.fetchall()
    conn.close()
    
    print("\n--- 💰 RELATÓRIO DE VENDAS ---")
    if not vendas:
        print("Nenhuma venda registrada ainda.")
    
    for v in vendas:
        # v[0]=ID, v[1]=Data, v[2]=Nome Cliente, v[3]=Total
        print(f"Pedido #{v[0]} | Data: {v[1]}")
        print(f"Cliente: {v[2]}")
        print(f"Total: R$ {v[3]:.2f}")
        print("-" * 30)

def nova_venda():
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Escolher Cliente
    print("\n--- PASSO 1: Selecione o Cliente ---")
    cursor.execute("SELECT id, nome FROM Clientes")
    clientes = cursor.fetchall()
    for c in clientes:
        print(f"ID: {c[0]} | Nome: {c[1]}")
    
    try:
        id_cliente = int(input("Digite o ID do cliente: "))
    except ValueError:
        print("❌ ID inválido!")
        return

    # 2. Criar Pedido
    data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO Pedidos (data, id_cliente, valor_total) VALUES (?, ?, ?)", 
                   (data_hoje, id_cliente, 0))
    conn.commit()
    id_pedido = cursor.lastrowid 
    print(f"✅ Pedido #{id_pedido} iniciado!")

    # 3. Adicionar Produtos
    valor_total_pedido = 0.0

    while True:
        print("\n--- PASSO 2: Adicionar Produto ---")
        cursor.execute("SELECT id, nome, preco FROM Produtos")
        produtos = cursor.fetchall()
        for p in produtos:
            print(f"ID: {p[0]} | {p[1]} - R$ {p[2]:.2f}")
            
        opcao_prod = input("Digite o ID do produto (ou '0' para encerrar): ")
        if opcao_prod == '0':
            break

        cursor.execute("SELECT preco FROM Produtos WHERE id = ?", (opcao_prod,))
        resultado = cursor.fetchone()
        
        if resultado:
            preco = resultado[0]
            qtd = int(input(f"Quantidade: "))
            total_item = preco * qtd
            
            cursor.execute("""
                INSERT INTO Pedidos_Itens (id_pedido, id_produto, valor_unitario, quantidade, total)
                VALUES (?, ?, ?, ?, ?)
            """, (id_pedido, opcao_prod, preco, qtd, total_item))
            
            valor_total_pedido += total_item
            print(f"➕ Item adicionado! Subtotal: R$ {valor_total_pedido:.2f}")
        else:
            print("❌ Produto não encontrado.")

    
    def ver_detalhes_pedido():
     conn = conectar()
    cursor = conn.cursor()
    
    id_pedido = input("\nDigite o número do Pedido para ver os itens: ")
    
    # Busca o cabeçalho (Quem comprou)
    cursor.execute("""
        SELECT Clientes.nome, Pedidos.data 
        FROM Pedidos 
        JOIN Clientes ON Pedidos.id_cliente = Clientes.id
        WHERE Pedidos.id = ?
    """, (id_pedido,))
    pedido = cursor.fetchone()
    
    if not pedido:
        print("❌ Pedido não encontrado.")
        conn.close()
        return

    print(f"\n--- 🎂 ITENS DO PEDIDO #{id_pedido} ---")
    print(f"Cliente: {pedido[0]} | Data: {pedido[1]}")
    print("-" * 40)
    
    # Busca os itens (Quais bolos)
    # Aqui fazemos o JOIN entre 'Pedidos_Itens' e 'Produtos'
    cursor.execute("""
        SELECT Produtos.nome, Pedidos_Itens.quantidade, Pedidos_Itens.valor_unitario, Pedidos_Itens.total
        FROM Pedidos_Itens
        JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id
        WHERE Pedidos_Itens.id_pedido = ?
    """, (id_pedido,))
    
    itens = cursor.fetchall()
    
    for item in itens:
        # item[0]=Nome Bolo, item[1]=Qtd, item[2]=Preço Unit, item[3]=Total Item
        print(f"{item[1]}x {item[0]:<20} | R$ {item[3]:.2f}")
    
    print("-" * 40)
    conn.close()
    
    
    
    
    # 4. Finalizar
    cursor.execute("UPDATE Pedidos SET valor_total = ? WHERE id = ?", (valor_total_pedido, id_pedido))
    conn.commit()
    conn.close()
    
    print("---------------------------------------------")
    print(f"🎉 Venda Finalizada! Pedido #{id_pedido}")
    print(f"💰 Valor Final: R$ {valor_total_pedido:.2f}")
    print("---------------------------------------------")

def ver_detalhes_pedido():
    conn = conectar()
    cursor = conn.cursor()
    
    print("\n--- 📋 DETALHES DO PEDIDO ---")
    try:
        id_pedido = int(input("Digite o ID do pedido: "))
    except ValueError:
        print("❌ ID inválido!")
        return
    
    cursor.execute("""
        SELECT Pedidos.id, Pedidos.data, Clientes.nome, Pedidos.valor_total
        FROM Pedidos
        JOIN Clientes ON Pedidos.id_cliente = Clientes.id
        WHERE Pedidos.id = ?
    """, (id_pedido,))
    
    pedido = cursor.fetchone()
    
    if not pedido:
        print("❌ Pedido não encontrado.")
        conn.close()
        return
    
    print(f"\nPedido #{pedido[0]} | Data: {pedido[1]}")
    print(f"Cliente: {pedido[2]}")
    print(f"Total: R$ {pedido[3]:.2f}")
    print("\n--- ITENS DO PEDIDO ---")
    
    cursor.execute("""
        SELECT Produtos.nome, Pedidos_Itens.quantidade, Pedidos_Itens.valor_unitario, Pedidos_Itens.total
        FROM Pedidos_Itens
        JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id
        WHERE Pedidos_Itens.id_pedido = ?
    """, (id_pedido,))
    
    itens = cursor.fetchall()
    
    for item in itens:
        print(f"{item[0]} | Qtd: {item[1]} | R$ {item[2]:.2f} un. | Subtotal: R$ {item[3]:.2f}")
    
    conn.close()

def exportar_para_excel():
    print("\n--- GERANDO RELATÓRIO EXCEL (CSV) ---")
    conn = conectar()
    cursor = conn.cursor()
    
    # Vamos pegar uma visão completa: Venda, Data, Cliente e Itens
    # Aqui usamos um JOIN duplo para trazer o nome do cliente E o nome do produto
    sql = """
    SELECT 
        Pedidos.id as 'ID Pedido',
        Pedidos.data as 'Data',
        Clientes.nome as 'Cliente',
        Produtos.nome as 'Bolo',
        Pedidos_Itens.quantidade as 'Qtd',
        Pedidos_Itens.valor_unitario as 'Valor Unit.',
        Pedidos_Itens.total as 'Total Item'
    FROM Pedidos_Itens
    JOIN Pedidos ON Pedidos_Itens.id_pedido = Pedidos.id
    JOIN Clientes ON Pedidos.id_cliente = Clientes.id
    JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id
    ORDER BY Pedidos.id DESC
    """
    
    cursor.execute(sql)
    dados = cursor.fetchall()
    conn.close()
    
    if not dados:
        print("❌ Nenhuma venda para exportar.")
        return

    nome_arquivo = "relatorio_vendas.csv"
    
    try:
        # encoding='utf-8-sig' é vital para o Excel entender acentos (ç, ã, é)
        with open(nome_arquivo, mode='w', newline='', encoding='utf-8-sig') as arquivo:
            escritor = csv.writer(arquivo, delimiter=';') # Ponto e vírgula separa colunas no Excel BR
            
            # Escrevendo o Cabeçalho
            escritor.writerow(['ID Pedido', 'Data', 'Cliente', 'Bolo', 'Qtd', 'Preço Unit.', 'Total Item'])
            
            # Escrevendo os Dados
            escritor.writerows(dados)
            
        print(f"✅ Arquivo '{nome_arquivo}' criado na pasta do projeto!")
        print(f"📂 Caminho: {os.path.join(BASE_DIR, nome_arquivo)}")
        
    except PermissionError:
        print("⚠️  ERRO: O arquivo 'relatorio_vendas.csv' já está aberto no Excel.")
        print("Feche o arquivo e tente novamente.")

# --- MENU PRINCIPAL ---

inicializar_banco() # Garante que as tabelas existem antes de começar

while True:
    print("\n=== SISTEMA DE BOLOS ===")
    print("1. Cadastrar Cliente")
    print("2. Cadastrar Produto")
    print("3. Ver Cardápio")
    print("4. NOVA VENDA")
    print("5. Relatório de Vendas") 
    print("6. Detalhes de um Pedido (Para a Cozinha)")
    print("7.Exportar para Excel")
    print("0. Sair")
    
    opcao = input("\nOpção: ")

    if opcao == "1":
        cadastrar_cliente()
    elif opcao == "2":
        cadastrar_produto()
    elif opcao == "3":
        ver_cardapio()
    elif opcao == "4":
        nova_venda()
    elif opcao == "5":
        relatorio_vendas() # <--- Chama a função
    elif opcao == "6":
        ver_detalhes_pedido()
    elif opcao == "0":
        break
    elif opcao == "7":
         exportar_para_excel()
        
    print("Opção inválida!")




