import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import numpy as np
import time
from flask import Flask, jsonify, request

import io
import tempfile
from flask import Flask, render_template, request, send_file
import plotly.graph_objects as go

app = Flask(__name__)

############################ RANDOMIZAÇÃO/ORDENAÇÃO DE VETORES ############################

# Configuração do logging
logging.basicConfig(level=logging.INFO, # Define o nível de log como INFO
                    format='%(asctime)s - %(levelname)s - %(message)s', # Formato da mensagem de log
                    handlers=[
                        logging.FileHandler("debug.log"),   # Grava logs em um arqwuivo chamado debug.log
                        logging.StreamHandler() # Exibe logs no console
                    ])

# Definir uma classe base a herança das funcionalidade ORM (recurso de Mapeamento Objetio-Relacional)
Base = declarative_base()

# Classe para representar a tabela 'info_vetores' no db
class InfoVetores(Base):
    __tablename__ = 'info_vetores'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50))
    descricao = Column(String(255))
    tempo_execucao = Column(Float)
    numeros = relationship("NumerosVetor", back_populates="vetor")

# Classe NumerosVetor para representar a tabela 'numeros_vetor' no db
class NumerosVetor(Base):
    __tablename__ = 'numeros_vetor'
    id = Column(Integer, primary_key=True)
    numero = Column(Integer)
    vetor_id = Column(Integer, ForeignKey('info_vetores.id'))
    executado_com_random = Column(Boolean)
    vetor = relationship("InfoVetores", back_populates="numeros")

# Configuração do banco de dados MySQL
engine = create_engine('mysql+pymysql://root:@localhost/randomiza_db')  # Conexão com db randomiza_db
Base.metadata.create_all(engine)    # Criação das tabelas construídas anteriormente, caso ainda não existam

Session = sessionmaker(bind=engine) # Criar "fábrica" de sessões para a manipulação dos dados do db
session = Session() # Criar uma nova sessão no db

tamanho_do_vetor = 50000    # Tamanho do vetor de números inteiros
max_numero = 50000  # Valor máximo para os números inteiros no vetor
randomizar = True   # Variável controladora para definir se os números devem ser gerados de forma aleatória
num_execucoes = 3   # Qtde de execuções para gerar vetores diferentes

# Função para ordenar um array de números utilizando o algoritmo quicksort
def quick_sort(arr):
    if len(arr) <= 1:   # Validação: se o array <= 1 (ordenado ou vazio), sai da recusão
        return arr
    else:
        pivot = arr[len(arr) // 2]  # Utilizar o elemento do meio do array como pivô
        left = [x for x in arr if x < pivot]    # Criar lista com os elementos menos que o pivô
        middle = [x for x in arr if x == pivot] # Criar lista com os elementos iguais ao pivô, evitando iterações desnecessárias
        right = [x for x in arr if x > pivot]   # Criar lista com os elementos maiores que o pivô
        return quick_sort(left) + middle + quick_sort(right)    # Recursivamente, aplicar o ordenar o left e o right e concatenar com o middle

# Função para gerar um vetor de números inteiros únicos
def gerar_dados():
    if randomizar:  # Caso deseja-se gerar um vetor com números aleatórios
        np.random.seed(None)    # Gerar uma semente inicial aleatória a cada execução
    else:
        np.random.seed(0)   # Definir uma semente fixa, iniciando em 0
    return np.random.choice(max_numero, tamanho_do_vetor, replace=False)    # Gerar o vetor de números inteiros únicos

# Loop para gerar vetores de números inteiros únicos e armazená-los no db
for i in range(num_execucoes):
    logging.info(f"Iniciando a execução {i + 1}")# Registrar o início da execução
    start_time = time.time()    # Marcar o tempo de início da execução
    vetor = gerar_dados()   # Gerar um vetor de números inteiros não duplicados
    end_time = time.time()  # Marcar o tempo de término da execução

    tempo_execucao = end_time - start_time  # Calcular o tempo de execução

    logging.info(f"Finalizando a execução {i + 1}") # Registrar o término da execução
    logging.info(f"Tempo de execução {i + 1}: {tempo_execucao:.4f} segundos")   # Registrar o tempo de execução da randomização

    # Criar uma instância da classe InfoVetores para armazenar informações sobre o vetor no db
    info = InfoVetores(nome=f"Vetor_{i + 1}", descricao="Vetor de números inteiros únicos", tempo_execucao=tempo_execucao)
    session.add(info)   # Adiciona a instância na tabela InfoVetores
    session.flush()  # Flush para obter o ID antes do commit

    # Criar instâncias da classe NumerosVetor para armazenar os números do vetor no db
    numeros = [NumerosVetor(numero=num, executado_com_random=randomizar, vetor_id=info.id) for num in vetor]
    session.bulk_save_objects(numeros)  # Salvar todos os objetos na tabela NumerosVetor de uma só vez
    session.commit()    # Salvar as alterações no db

session.close() # Fechar a sessão do db

# Rotas da API Flask para interagir com os dados armazenados no banco de dados

# Rota principal - Mensagem de boas vindas
@app.route('/')
def indexVetor():
    return "Seja bem vindo a minha N2 - Server Side!"

# Rota que lista todos os vetores randomizados armazenados no db
@app.route('/vetores', methods=['GET'])
def listar_vetores():
    session = Session() # Abrir uma nova sessão do db
    vetores = session.query(InfoVetores).all()  # Consultar todos os vetores no db
    result = []
    for vetor in vetores:
        result.append({ # Adicionar informações sobre cada vetor à lista de resultados
            'id': vetor.id,
            'nome': vetor.nome,
            'descrição': vetor.descricao,
            'tempo de execução': vetor.tempo_execucao
        })
    session.close() # Fechar a sessão do db
    return jsonify(result)    # Retornar a resposta JSON com os detalhes do vetor

# Rota para fornecer as informações do vetor por meio do id
@app.route('/vetores/<int:id>', methods=['GET'])
def detalhes_vetor(id):
    session = Session() # Abrir uma nova sessão do db
    vetor = session.query(InfoVetores).filter_by(id=id).first()  # Consultar o vetor pelo ID fornecido
    if vetor:
        numeros = [num.numero for num in vetor.numeros] # Obtém os números do vetor
        response = {    # Criar uma resposta JSON com as informações do vetor e seus números correspondentes
            'id': vetor.id,
            'nome': vetor.nome,
            'descrição': vetor.descricao,
            'tempo de execução': vetor.tempo_execucao,
            'números': numeros
        }
        session.close() # Fechar a sessão do db
        return jsonify(response)    # Retornar a resposta JSON com os detalhes do vetor
    else:
        session.close() # Fechar a sessão do db
        return jsonify({"error": "Vetor não encontrado"}), 404  # Retornar um erro 404 se o vetor não foi encontrado

# Rota para realizar a ordenação dos vetores
@app.route('/ordenar_vetores/<int:id>', methods=['GET'])
def ordenar_vetores(id):
    session = Session() # Abrir uma nova sessão do db
    vetor = session.query(InfoVetores).filter_by(id=id).first()  # Consultar o vetor pelo ID fornecido

    if vetor:
        start_time = time.time()  # Registrar o tempo de início da ordenação
        numeros = session.query(NumerosVetor).filter_by(vetor_id=id).order_by(NumerosVetor.numero).all()    # Instanciar consulta
        numeros_ordenados = [num.numero for num in numeros]  # Obtém os números do vetor ordenado
        end_time = time.time()  # Registrar o tempo de término da ordenação
        tempo_execucao = end_time - start_time  # Calcular o tempo de execução da ordenação

        # Registrar os resultados, incluindo o tempo de execução
        resultado = {
            'vetor_id': vetor.id,
            'tempo_execucao': f"{tempo_execucao:.4f} segundos",
            'numeros_ordenados': numeros_ordenados
        }
        session.close() # Fechar a sessão do db
        return jsonify(resultado)    # Retornar a resposta JSON com os detalhes do vetor
    else:
        session.close() # Fechar a sessão do db
        return jsonify({"error": "Vetor não encontrado"}), 404 # Retornar um erro 404 se o vetor não foi encontrado

######################################### GRÁFICOS #########################################

#Rota para a página principal
@app.route('/geradorGraficos')
def indexGrafico():
    return render_template('index.html')

# Rota para geração do gráfico
@app.route('/gerarGrafico', methods=['GET','POST'])
def gerarGrafico():
    vetorX = list(map(float, request.form['vetorX'].split(',')))
    vetorY = list(map(float, request.form['vetorY'].split(',')))
    tipo_grafico = request.form['tipo_grafico']

# Gerar o gráfico correspondente
    if tipo_grafico == 'scatter':
        figura = go.Figure(data=go.Scatter(x=vetorX, y=vetorY, mode='markers', marker=dict(size=10, sizemode='diameter')))
    elif tipo_grafico == 'line':
        figura = go.Figure(data=go.Line(x=vetorX, y=vetorY))
    elif tipo_grafico == 'bar':
        figura = go.Figure(data=go.Bar(x=vetorX, y=vetorY))
    elif tipo_grafico == 'bubble':
        figura = go.Figure(data=go.Scatter(x=vetorX, y=vetorY, mode='markers', marker=dict(size=50, sizemode='diameter')))
    elif tipo_grafico == 'dot':
        figura = go.Figure(data=go.Scatter(x=vetorX, y=vetorY, mode='markers', marker=dict(size=10)))
    else:
        return 'Tipo de gráfico inválido'

# Converter gráfico para string json e enviá-la para front-end
    plot_json = figura.to_json()
    return render_template('index.html', plot_json = plot_json)

if __name__ == '__main__':
    app.run(debug=False)