import os
import asyncio
import httpx
import MetaTrader5 as mt5
#import tkinter as tk
#from tkinter import ttk

import tkinter as tk
from tkinter import ttk, messagebox

import threading
from PIL import Image, ImageTk
import shutil
import json
import winsound
import re
import time
import uuid
import datetime
import pandas as pd
from analise_symbolinfo3 import analisar_com_symbolinfo 
from analise_symbolinfo4 import analisar_com_symbolinfo4, SistemaDecisaoCompleto
from analise_tecnica_pura import AnalisadorTecnicoPuro, AnalisadorBookOfertas # testar
from neural_teste import RedeNeuralOpcoes
import sys
#from cerebro import SistemaOpcoesInteligente
from cerebro import rede


import pandas as pd
import traceback

import numpy as np

nome_programa = os.path.basename(__file__).replace('.py', '')

#rede = RedeNeuralOpcoes("modelo_opcoes.json")

# Novo sistema de ensemble
#sistema_ensemble = SistemaOpcoesInteligente()

sistema_ensemble = rede

# Verifica se o arquivo existe na pasta atual
print("Arquivos na pasta atual:", os.listdir('.'))
print("Caminho atual:", os.path.abspath('.'))

# Verifica especificamente o neural_teste.py
if os.path.exists('neural_teste.py'):
    print("✓ neural_teste.py encontrado!")
else:
    print("✗ neural_teste.py NÃO encontrado!")
    print("Verifique o nome do arquivo (case sensitive)")



#--------------------------------------------------------------
class TrailingStop:
    def __init__(self, distancia=0.02):
        self.distancia = distancia
        self.preco_maximo = None
        self.preco_minimo = None
        self.preco_entrada = None
        self.trailing_ativado = False
        self.percentual_ativacao = 0.01  # 1% de lucro para ativar
    
    def configurar(self, preco_entrada, posicao):
        self.preco_entrada = preco_entrada
        self.posicao = posicao  # 'compra' ou 'venda'
        self.preco_maximo = None
        self.preco_minimo = None
        self.trailing_ativado = False
        return self
    
    def verificar_saida(self, preco_atual):
        # Posição de COMPRA (lucra com alta)
        if self.posicao == 'compra':
            if self.preco_maximo is None or preco_atual > self.preco_maximo:
                self.preco_maximo = preco_atual
            
            # Ativa após 1% de lucro
            if not self.trailing_ativado and self.preco_entrada:
                lucro = (preco_atual - self.preco_entrada) / self.preco_entrada
                if lucro >= self.percentual_ativacao:
                    self.trailing_ativado = True
            
            if not self.trailing_ativado:
                return 'MANTER'
            
            stop = self.preco_maximo * (1 - self.distancia)
            return 'SAIR' if preco_atual <= stop else 'MANTER'
        
        # Posição de VENDA (lucra com baixa)
        elif self.posicao == 'venda':
            if self.preco_minimo is None or preco_atual < self.preco_minimo:
                self.preco_minimo = preco_atual
            
            # Ativa após 1% de lucro
            if not self.trailing_ativado and self.preco_entrada:
                lucro = (self.preco_entrada - preco_atual) / self.preco_entrada
                if lucro >= self.percentual_ativacao:
                    self.trailing_ativado = True
            
            if not self.trailing_ativado:
                return 'MANTER'
            
            stop = self.preco_minimo * (1 + self.distancia)
            return 'SAIR' if preco_atual >= stop else 'MANTER'
        
        return 'MANTER'
    
    def reset(self):
        self.preco_maximo = None
        self.preco_minimo = None
        self.preco_entrada = None
        self.trailing_ativado = False
        return self


# ===== ADICIONE NO INÍCIO DO SEU CÓDIGO =====
# Dicionário para armazenar os trailing stops por ativo
trailing_stops = {}

# Configuração da distância do trailing (2% = 0.02)
DISTANCIA_TRAILING = 0.02  # 2%
TRAILING_ATIVADO = True    # Ligar/desligar trailing stop

#------------------------------------------------------------




ultimo_diff = {} 

# 2. Criar analisador
analisador = AnalisadorTecnicoPuro()

CONFIG_FILE = "config.json"
# Configurações do bot
TOKEN = "2093745787:AAEDZew3QqB6eMQEZwjcFxo22TU_PL74i-s"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"
CHAT_ID_DEFAULT = "@Minhasopcoes"

TEXT_PATH = "C:/Users/CI_158/AppData/Roaming/MetaQuotes/Terminal/Common/Files/mens.txt"
PATH = "C:/Users/CI_158/AppData/Roaming/MetaQuotes/Terminal/698B86206820B42976F30D28CAC50412/MQL5/Files/"
TEXT_ATIVAS = "C:/Users/CI_158/AppData/Roaming/MetaQuotes/Terminal/Common/Files/opc_ativas.txt"
ORDEM_PATH="C:/Users/CI_158/AppData/Roaming/MetaQuotes/Terminal/Common/Files/ordem.json"


# defina os horários de funcionamento
HORARIO_INICIO = datetime.time(10, 5)   # 09:00
HORARIO_FIM    = datetime.time(17,52 )  #17, 40 18:00

#PRECOS EM OBSERVADOS
MENOR_PRECO_ACEITO=0.10
MAIOR_PRECO_ACEITO=1.70
# Dicionários
ATIVOS = {}
OBSERVAR = {}  # ativos observados via /ver
FINALIZADOS={}
PAUSADO={}
NIVEIS_ATIVOS = {}

ULTIMA_IMAGEM = "ultima_imagem.png"
ULTIMA_IMAGEM_NOME = ""
ATIVOS_PATH = "ativos.json"
ATIVOS_FINALIZADOS_PATH = "finalizados.json"
ALERTA_ATUAL = ""   # começa vazio
ATIVO_COM_ALERTA=""
ULTIMA_MSG=""
NOVA_MSG=""
tree_finalizados = None
melhor_entrada_label=None
ESTRATEGIAS_ruins=["BLOQUEAR","EVITAR"]
ANALISE_ESTRATEGIA=""
VL_HUMANO_ZERADO= 4
# Variáveis globais de filtro (serão inicializadas na GUI)
MOSTRAR_MSGS = True
MOSTRAR_FOTOS = True
MOSTRAR_PYTHON = True
FILTRAR_MENSAGEM = True
MOSTRAR_FOTOS_CARTEIRA=True
SOM=True
APENAS_MSGS_STOP=True

INTENSAO= 0 # 0 todos, 1 fraco, 2 forte
LIMIAR_PERDA=0.02
SENSIBILIDADE_ENTRADA= 2 # 0 baixa, 1 media, 2 alta
CAPTAR_OPCAO=True #capturar opcao recebida por mensagem
AUTOMATIZAR=True #ligar automatizador

QTD_AUTO=500 #quantidade de opcoes do robo
IDENTIFICADOR_ROBO= 25.0#testar 45    #31.0 #identificar robo (MELHOR ATE AGORA)
REGRA2CENTS= False
QTD_ESPECIAL=200 #QUANTIDADE EXTRA PARA BOAS ENTRADAS
PREJUIZO_MAX_ZERADO = QTD_AUTO*0.05
ROBO_HR=27
ROBO_AR=28
ROBO_AA=29
ROBO_AC=30

UMA_OPCAO_P_LETRA= False #limitar mais de um tipo opcao por mes
UMA_OPCAO_P_LETRA_por_ROBO= True #limitar a uma opção por robo
FINALIZAR_OP_ROBO_STOP_LOSS=True #finaliza o robo ao perder 
FINALIZAR_OP_ROBO_STOP_MINI_SL=True # finaliza antes do loss
FILTRAR_SINAIS= True
MANTER_OBS=True #manter na tabela observados encerrados em MINI Stop LOSS
GATILHO_DIFF_PRECO=0.02 #MELHOR ATE AGORA era 0.02 

# --- CONSTANTES ---

REFORCO_PROSITIVO = False  # Controla se zera operações contra tendência NA FUNCAO DE INTENSIDADE se for contra a tendencia zera o valor de saida

tickers_STATUS = {}

MIICRO_TENDENCIA=None

ultimo_positivo5 = {}

#stop_loss_padrao
STOP_LOSS_PADRAO=5.0
STOP_LOSS_PADRAO_POSITIVO=2.0
#mini_stop_loss
MINI_STOP_GAIN_PADRAO=26

# Variável global para definir intervalo de bloqueio (em segundos)
INTERVALO_BLOQUEIO = 300   # 5 minutos
# limiar mínimo de força (percentual) para considerar movimento válido
LIMIAR_FORCA = 52.0
# Dicionário global para armazenar textos já enviados e o horário do envio
mensagens_enviadas = {}
MAPA_ATIVOS = {
    "PETR": "PETR4",
    "VALE": "VALE3",
    "ITUB": "ITUB4",
    "BBDC": "BBDC4",
    "BBAS": "BBAS3",
    "ABEV": "ABEV3",
    "MGLU": "MGLU3",
    "LREN": "LREN3",
    "SUZB": "SUZB3",
    "GGBR": "GGBR4",
    "USIM": "USIM5",
    "CSNA": "CSNA3",
    "BRFS": "BRFS3",
    "JBSS": "JBSS3",
    "ELET": "ELET3",  # pode ser ELET3 ou ELET6
}

#SUPORTE_DIARIO = None
#RESISTENCIA_DIARIA = None


#se estiver fora do tempo zerar os valores da tabela observados


def carregar_configuracoes():
    """Carrega configurações do arquivo JSON se existir"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                import json
                config_data = json.load(f)
                
                # Atualizar variáveis globais
                globals_to_update = [
                    'TOKEN', 'CHAT_ID_DEFAULT', 'TEXT_PATH', 'PATH', 'TEXT_ATIVAS',
                    'ATIVOS_PATH', 'ATIVOS_FINALIZADOS_PATH', 'MENOR_PRECO_ACEITO',
                    'MAIOR_PRECO_ACEITO', 'AUTOMATIZAR', 'QTD_AUTO', 'IDENTIFICADOR_ROBO',
                    'REGRA2CENTS', 'QTD_ESPECIAL', 'PREJUIZO_MAX_ZERADO', 'UMA_OPCAO_P_LETRA',
                    'FINALIZAR_OP_ROBO_STOP_LOSS', 'FINALIZAR_OP_ROBO_STOP_MINI_SL',
                    'FILTRAR_SINAIS', 'MANTER_OBS', 'GATILHO_DIFF_PRECO','LIMIAR_PERDA' ,'REFORCO_PROSITIVO',
                    'STOP_LOSS_PADRAO', 'MINI_STOP_GAIN_PADRAO', 'INTERVALO_BLOQUEIO',
                    'LIMIAR_FORCA', 'INTENSAO', 'SENSIBILIDADE_ENTRADA'
                ]
                
                for key in globals_to_update:
                    if key in config_data:
                        globals()[key] = config_data[key]
                
                # Atualizar BASE_URL com novo TOKEN
                globals()['BASE_URL'] = f"https://api.telegram.org/bot{TOKEN}/"
                
                # Converter horários
                if 'HORARIO_INICIO' in config_data:
                    hh, mm = config_data['HORARIO_INICIO'].split(':')
                    globals()['HORARIO_INICIO'] = datetime.time(int(hh), int(mm))
                
                if 'HORARIO_FIM' in config_data:
                    hh, mm = config_data['HORARIO_FIM'].split(':')
                    globals()['HORARIO_FIM'] = datetime.time(int(hh), int(mm))
                    
                print("✅ Configurações carregadas de CONFIG_FILE")
    except Exception as e:
        print(f"⚠️ Erro ao carregar configurações: {e}")

# Chame a função após definir as variáveis globais
carregar_configuracoes()


def dentro_horario():
    agora = datetime.datetime.now().time()  # note o datetime.datetime
    return HORARIO_INICIO <= agora <= HORARIO_FIM
# --- Persistência ---
def carregar_ativos():
    global ATIVOS, MINI_STOP_GAIN_PADRAO
    try:
        if os.path.exists(ATIVOS_PATH):
            with open(ATIVOS_PATH, "r", encoding="utf-8") as f:
                ATIVOS = json.load(f)

            for ativo, dados in list(ATIVOS.items()):

                # garantir stop loss
                if "stop_loss_pct" not in dados or "stop_loss_valor" not in dados:
                    stop_loss_pct =  5.0 #MINI_STOP_GAIN_PADRAO
                    entrada = dados.get("entrada", 0)
                    tipo = dados.get("tipo", "compra")
                    if tipo == "compra":
                        stop_loss_valor = entrada * (1 - stop_loss_pct/100.0)
                    else:
                        stop_loss_valor = entrada * (1 + stop_loss_pct/100.0)
                    dados["stop_loss_pct"] = stop_loss_pct
                    dados["stop_loss_valor"] = stop_loss_valor
                # garantir mini stop
                if "mini_stop_pct" not in dados:
                    dados["mini_stop_pct"] = 30.0
                if "intensidade" not in dados:
                    dados["intensidade"] = 0.1
                if "historico" not in dados:
                    dados["historico"] = "s.h."
                if "ia_resultado" not in dados:
                    dados["ia_resultado"] = "ia_resultado"
                if "ia_estado" not in dados:
                    dados["ia_estado"] = "ia_estado"
    
    except Exception as e:
        print("⚠️ Erro ao carregar ativos:", e)


def salvar_ativos():
    global STOP_LOSS_PADRAO
    for ativo, dados in list(ATIVOS.items()):

        if "stop_loss_pct" not in dados or "stop_loss_valor" not in dados:
            stop_loss_pct = STOP_LOSS_PADRAO
            entrada = dados.get("entrada", 0)
            tipo = dados.get("tipo", "compra")
            if tipo == "compra":
                stop_loss_valor = entrada * (1 - stop_loss_pct/100.0)
            else:
                stop_loss_valor = entrada * (1 + stop_loss_pct/100.0)
            dados["stop_loss_pct"] = stop_loss_pct
            dados["stop_loss_valor"] = stop_loss_valor
        if "mini_stop_pct" not in dados:
            dados["mini_stop_pct"] = 30.0
        if "intensidade" not in dados:
            dados["intensidade"] = 0.1
        if "historico" not in dados:
            dados["historico"] = "s.h."
        if "ia_resultado" not in dados:
            dados["ia_resultado"] = "ia_resultado"
        if "ia_estado" not in dados:
            dados["ia_estado"] = "ia_estado"    
    
    with open(ATIVOS_PATH, "w", encoding="utf-8") as f:
        #json.dump(ATIVOS, f, indent=4, ensure_ascii=False)
        json.dump(ATIVOS, f, indent=4, ensure_ascii=False, default=str) 


def carregar_finalizados():
    global FINALIZADOS
    if os.path.exists("finalizados.json"):
        try:
            with open("finalizados.json", "r", encoding="utf-8") as f:
                FINALIZADOS = json.load(f)
        except Exception as e:
            print("⚠️ Erro ao carregar finalizados.json:", e)
            FINALIZADOS = {}
    else:
        FINALIZADOS = {}







def salvar_finalizados():            
    with open(ATIVOS_FINALIZADOS_PATH, "w", encoding="utf-8") as f:
        #json.dump(FINALIZADOS, f, indent=4, ensure_ascii=False)
        json.dump(FINALIZADOS, f, indent=4, ensure_ascii=False, default=str) 

carregar_ativos()
carregar_finalizados()
# def finalizar_ativo(ativo_, valor_final):
#     global ATIVOS, OBSERVAR, FINALIZADOS,NOVA_MSG ,tree_finalizados, melhor_entrada_label, ANALISE_ESTRATEGIA
#     ativo = ativo_.upper()
#     if ativo in ATIVOS:
#         dados = ATIVOS[ativo].copy()
#         qtd = dados.get("qtd", 1.0)
#         tipo = dados.get("tipo", "compra")
#         entrada = dados.get("entrada", 0.0)
#         mini_stop_pct = dados.get("mini_stop_pct", 30.0)
#         max_diff = dados.get("max_diff", entrada)
#         mini_stop_valor = max_diff * (1 - mini_stop_pct/100.0)
#         ultimo_status= dados.get("ultimo_status")
#         diff_unit = valor_final - entrada if tipo == "compra" else entrada - valor_final
#         resultado_final = diff_unit * qtd
#         intensidade= dados.get("intensidade")
#         historico= dados.get("historico")
#         ia_resultado= dados.get("ia_resultado")
#         ia_estado= dados.get("ia_estado")

#         # status final positivo/negativo
#         status_final = "positivo" if resultado_final >= 0 else "negativo"

#         st_loss = (f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️ \n FECHANDO NO PREJUIZO Operação ENCERRADA: {ativo}\n"
#                    f"Entrada: {entrada:.2f} | Final: {valor_final:.2f} | Qtd: {qtd}\n"
#                    f"Tipo: {tipo} | Resultado Final: {resultado_final:.2f} | Status: {ultimo_status}")

#         mini_st_loss = (f"✅✅✅✅✅✅✅✅\nFECHANDO COM LUCRO \n ALERTA MINI STOP atingido em {ativo}!\n"
#                         f"Ganho atual: {resultado_final:.2f} < Mini Stop: {mini_stop_valor:.2f} "
#                         f"({mini_stop_pct:.1f}% abaixo do máximo) | Status: {ultimo_status}")

#         resposta = st_loss if resultado_final < 0 else mini_st_loss

#         # remover com segurança
#         ATIVOS.pop(ativo, None)
#         OBSERVAR.pop(ativo, None)
#         salvar_ativos()
        
#         if resultado_final >= 0 and MANTER_OBS:
#             adicionar_opcao(ativo) 

#         # --- Gerar identificador único apenas ao finalizar ---
#         op_id = str(uuid.uuid4())

#         FINALIZADOS[op_id] = {
#             "ativo": ativo,
#             "entrada": entrada,
#             "qtd": qtd,
#             "tipo": tipo,
#             "r_fim": round(resultado_final, 2),
#             "mini_stop_pct": mini_stop_pct,
#             "ultimo_status":  status_final,  #ultimo_status,
#             "intensidade" : intensidade,
#             "historico": historico,
#             "ia_resultado":ia_resultado,
#             "ia_estado":ia_estado
#         }
        
#         # Converter dicionário para DataFrame
#         df_finalizados = pd.DataFrame.from_dict(FINALIZADOS, orient='index')

# # Executar análise
         
#         pior_historico ="*"
#         me_estr, pior_historico = analise_detalhada_alta_intensidade(df_finalizados, limiar_intensidade=52)
#         me_estr2, pior_estr2 = analise_detalhada_alta_intensidade2(df_finalizados, limiar_intensidade=52)
        
#         ANALISE_ESTRATEGIA= str( me_estr2)+"|pior:"+str(pior_estr2)
#         #NOVA_MSG= f"Melhor estratégia: { str( ANALISE_ESTRATEGIA) }"    
        
#         # Garantir que temos uma string para o label
        
#         ESTRATEGIAS_ruins=["BLOQUEAR","EVITAR"]  #ADICIONAR AS QUE FOREM FILTRADAS DEPOIS PIOR_ESTR2
    
#     # Atualizar label (se existir)
    
#         #if 'melhor_entrada_label' in globals() and melhor_entrada_label:
#         #    
#         # 4. Após fechar operação, registrar resultado
        
#         #ia-----------
        
# #-------------------------------------------------------------------

#         tipo_inverso = "compra" if tipo == "venda" else "venda"
#         enviar_ordem(ativo, tipo_inverso, qtd, "0")
        
#         salvar_finalizados()       

#         lucro_percentual = (diff_unit - entrada) / entrada * 100
#         #rede.registrar_resultado(ia_resultado, lucro_percentual) 
       
#         # ✅ CORRETO
#         estado_completo = ATIVOS.get(ativo, {}).get('ia_estado')
#         # if estado_completo:
#         #     rede.registrar_resultado(estado_completo, lucro_percentual)
#         # else:
#         #     print(f"⚠️ Estado não encontrado para {ativo}")


#         if estado_completo:
#             try:
#                 recompensa = rede.registrar_resultado(estado_completo, lucro_percentual)
#                 print(f"✅ Rede calibrada: {lucro_percentual:.2f}%")
#             except Exception as e:
#                 print(f"❌ Erro ao calibrar: {e}")
#         else:
#             print(f"⚠️ Estado não encontrado para {ativo}")


           

#         # Atualizar tabela no GUI
#         if tree_finalizados:
            
#             for item in tree_finalizados.get_children():
#                 tree_finalizados.delete(item)
#             for op_id_f, dados_f in FINALIZADOS.items():
#                 status_tag = "positivo" if dados_f.get("ultimo_status") == "positivo" else "negativo"
#                 tree_finalizados.insert("", "end", values=(
#                     dados_f.get("ativo", ""),
#                     f"{dados_f.get('entrada', 0.0):.2f}",
#                     dados_f.get("qtd", 0.0),
#                     dados_f.get("tipo", ""),
#                     f"{dados_f.get('r_fim', 0.0):.2f}",
#                     dados_f.get("mini_stop_pct", 0.0),
#                     dados_f.get("ultimo_status", ""),
#                     dados_f.get("intensidade", 0.0),
#                     dados_f.get("historico", "")

#                 ), tags=(status_tag,))
        
        
            
        



#         return resposta 

def serializar_estado_seguro(estado):
    """Remove referências circulares e converte numpy para Python"""
    if estado is None:
        return None
    if isinstance(estado, dict):
        return {k: serializar_estado_seguro(v) for k, v in estado.items() 
                if k not in ['ensemble', 'modelo', 'scaler', 'rf_model', 'gb_model', 
                            'xgb_model', 'lstm_model', 'device']}
    if isinstance(estado, list):
        return [serializar_estado_seguro(v) for v in estado]
    if isinstance(estado, np.ndarray):
        return estado.tolist()
    if isinstance(estado, (np.float64, np.float32)):
        return float(estado)
    if isinstance(estado, (np.int64, np.int32)):
        return int(estado)
    if isinstance(estado, datetime.datetime):
        return estado.isoformat()
    try:
        json.dumps(estado)
        return estado
    except:
        return str(estado)


def finalizar_ativo(ativo_, valor_final):
    global ATIVOS, OBSERVAR, FINALIZADOS, NOVA_MSG, tree_finalizados, melhor_entrada_label, ANALISE_ESTRATEGIA
    ativo = ativo_.upper()
    
    if ativo in ATIVOS:
        dados = ATIVOS[ativo].copy()
        qtd = dados.get("qtd", 1.0)
        tipo = dados.get("tipo", "compra")
        entrada = dados.get("entrada", 0.0)
        mini_stop_pct = dados.get("mini_stop_pct", 30.0)
        max_diff = dados.get("max_diff", entrada)
        mini_stop_valor = max_diff * (1 - mini_stop_pct/100.0)
        ultimo_status = dados.get("ultimo_status")
        diff_unit = valor_final - entrada if tipo == "compra" else entrada - valor_final
        resultado_final = diff_unit * qtd
        intensidade = dados.get("intensidade")
        historico = dados.get("historico")
        ia_resultado = dados.get("ia_resultado")
        ia_estado = dados.get("ia_estado")  # <-- Pega a string JSON

        # status final positivo/negativo
        status_final = "positivo" if resultado_final >= 0 else "negativo"

        st_loss = (f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️ \n FECHANDO NO PREJUIZO Operação ENCERRADA: {ativo}\n"
                   f"Entrada: {entrada:.2f} | Final: {valor_final:.2f} | Qtd: {qtd}\n"
                   f"Tipo: {tipo} | Resultado Final: {resultado_final:.2f} | Status: {ultimo_status}")

        mini_st_loss = (f"✅✅✅✅✅✅✅✅\nFECHANDO COM LUCRO \n ALERTA MINI STOP atingido em {ativo}!\n"
                        f"Ganho atual: {resultado_final:.2f} < Mini Stop: {mini_stop_valor:.2f} "
                        f"({mini_stop_pct:.1f}% abaixo do máximo) | Status: {ultimo_status}")

        resposta = st_loss if resultado_final < 0 else mini_st_loss

        # ============================================
        # ✅ 1. ENVIAR ORDEM DE FECHAMENTO
        # ============================================
        tipo_inverso = "compra" if tipo == "venda" else "venda"
        enviar_ordem(ativo, tipo_inverso, qtd, "0")

        # ============================================
        # ✅ 2. CALCULAR LUCRO
        # ============================================
        lucro_percentual = diff_unit / entrada * 100
        print(f"📈 {ativo} - Lucro: {lucro_percentual:.2f}%")

        # ============================================
        # ✅ 3. CALIBRAR REDE NEURAL (CORRIGIDO!)
        # ============================================
        if ia_estado:
            try:
                # 🔥 A função registrar_resultado já converte string JSON para dict automaticamente!
                rede.registrar_resultado(ia_estado, lucro_percentual)
                print(f"✅ Rede calibrada com lucro: {lucro_percentual:.2f}%")
                
                # Mostrar estatísticas (com segurança)
                try:
                    stats = rede.get_estatisticas()
                    if stats and isinstance(stats, dict):
                        print("📊 Estatísticas da rede:")
                        print(f"   Total de operações: {stats.get('total_operacoes', 0)}")
                        print(f"   Taxa de acerto: {stats.get('taxa_acerto', 0):.1f}%")
                        print(f"   Lucro médio: {stats.get('lucro_medio', 0):.2f}%")
                        print(f"   Lucro total: {stats.get('lucro_total', 0):.2f}")
                except Exception as e_stats:
                    print(f"⚠️ Erro ao obter estatísticas: {e_stats}")
                    
            except Exception as e:
                print(f"❌ Erro ao calibrar rede: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ Estado não encontrado para {ativo} - pulando calibração")

        # ============================================
        # ✅ 4. SALVAR EM FINALIZADOS
        # ============================================
        op_id = str(uuid.uuid4())
        FINALIZADOS[op_id] = {
            "ativo": ativo,
            "entrada": entrada,
            "qtd": qtd,
            "tipo": tipo,
            "r_fim": round(resultado_final, 2),
            "mini_stop_pct": mini_stop_pct,
            "ultimo_status": status_final,
            "intensidade": intensidade,
            "historico": historico,
            "ia_resultado": ia_resultado,
            "ia_estado": ia_estado,  # <-- Mantém como string JSON
            "data_fechamento": datetime.datetime.now().isoformat(),
            "lucro_percentual": round(lucro_percentual, 2)
        }

        # ============================================
        # ✅ 5. REMOVER DE ATIVOS
        # ============================================
        ATIVOS.pop(ativo, None)
        OBSERVAR.pop(ativo, None)
        
        # ============================================
        # ✅ 6. SALVAR ARQUIVOS
        # ============================================
        salvar_ativos()
        salvar_finalizados()

        # ============================================
        # ✅ 7. ANÁLISE E ATUALIZAÇÃO DA GUI
        # ============================================ 
        if MANTER_OBS and (resultado_final >= 0 or abs(resultado_final) < PREJUIZO_MAX_ZERADO):
    
        #if resultado_final >= 0 and MANTER_OBS:
            adicionar_opcao(ativo)

        # Converter dicionário para DataFrame
        df_finalizados = pd.DataFrame.from_dict(FINALIZADOS, orient='index')

        # Executar análise
        pior_historico = "*"
        me_estr, pior_historico = analise_detalhada_alta_intensidade(df_finalizados, limiar_intensidade=52)
        me_estr2, pior_estr2 = analise_detalhada_alta_intensidade2(df_finalizados, limiar_intensidade=52)
        
        ANALISE_ESTRATEGIA = str(me_estr2) + "|pior:" + str(pior_estr2)

        # Atualizar tabela no GUI
        if tree_finalizados:
            for item in tree_finalizados.get_children():
                tree_finalizados.delete(item)
            for op_id_f, dados_f in FINALIZADOS.items():
                status_tag = "positivo" if dados_f.get("ultimo_status") == "positivo" else "negativo"
                tree_finalizados.insert("", "end", values=(
                    dados_f.get("ativo", ""),
                    f"{dados_f.get('entrada', 0.0):.2f}",
                    dados_f.get("qtd", 0.0),
                    dados_f.get("tipo", ""),
                    f"{dados_f.get('r_fim', 0.0):.2f}",
                    dados_f.get("mini_stop_pct", 0.0),
                    dados_f.get("ultimo_status", ""),
                    dados_f.get("intensidade", 0.0),
                    dados_f.get("historico", "")
                ), tags=(status_tag,))

        return resposta


# def finalizar_ativo(ativo_, valor_final):
#     global ATIVOS, OBSERVAR, FINALIZADOS, NOVA_MSG, tree_finalizados, melhor_entrada_label, ANALISE_ESTRATEGIA
#     ativo = ativo_.upper()
    
#     if ativo in ATIVOS:
#         dados = ATIVOS[ativo].copy()
#         qtd = dados.get("qtd", 1.0)
#         tipo = dados.get("tipo", "compra")
#         entrada = dados.get("entrada", 0.0)
#         mini_stop_pct = dados.get("mini_stop_pct", 30.0)
#         max_diff = dados.get("max_diff", entrada)
#         mini_stop_valor = max_diff * (1 - mini_stop_pct/100.0)
#         ultimo_status = dados.get("ultimo_status")
#         diff_unit = valor_final - entrada if tipo == "compra" else entrada - valor_final
#         resultado_final = diff_unit * qtd
#         intensidade = dados.get("intensidade")
#         historico = dados.get("historico")
#         ia_resultado = dados.get("ia_resultado")
#         ia_estado = dados.get("ia_estado")  # <-- ✅ PEGA O ESTADO

#         # status final positivo/negativo
#         status_final = "positivo" if resultado_final >= 0 else "negativo"

#         st_loss = (f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️ \n FECHANDO NO PREJUIZO Operação ENCERRADA: {ativo}\n"
#                    f"Entrada: {entrada:.2f} | Final: {valor_final:.2f} | Qtd: {qtd}\n"
#                    f"Tipo: {tipo} | Resultado Final: {resultado_final:.2f} | Status: {ultimo_status}")

#         mini_st_loss = (f"✅✅✅✅✅✅✅✅\nFECHANDO COM LUCRO \n ALERTA MINI STOP atingido em {ativo}!\n"
#                         f"Ganho atual: {resultado_final:.2f} < Mini Stop: {mini_stop_valor:.2f} "
#                         f"({mini_stop_pct:.1f}% abaixo do máximo) | Status: {ultimo_status}")

#         resposta = st_loss if resultado_final < 0 else mini_st_loss

#         # ============================================
#         # ✅ 1. ENVIAR ORDEM DE FECHAMENTO
#         # ============================================
#         tipo_inverso = "compra" if tipo == "venda" else "venda"
#         enviar_ordem(ativo, tipo_inverso, qtd, "0")

#         # ============================================
#         # ✅ 2. CALCULAR LUCRO
#         # ============================================
#         lucro_percentual = diff_unit / entrada * 100
#         # lucro =      0.64
        
#         #if resultado_final >= 0: lucro_percentual=0.20 

#         print(f"📈 {ativo} - Lucro: {lucro_percentual:.2f}%")

#         # ============================================
#         # ✅ 3. CALIBRAR REDE NEURAL (ANTES DE REMOVER!)
#         # ============================================
#         # if ia_estado:
#         #     try:
#         #         # Verificar se tem 'metricas'
#         #         if 'metricas' in ia_estado:
#         #             recompensa = rede.registrar_resultado(ia_estado, lucro_percentual)
#         #             print(f"✅ Rede calibrada: {recompensa:.2f}")
                    
#         #             # Mostrar estatísticas
#         #             stats = rede.get_estatisticas()
#         #             print(f"📊 Taxa de acerto: {stats['taxa_acerto']:.1f}%")
#         #             print(f"   Total: {stats['total_operacoes']}")
#         #         else:
#         #             print(f"⚠️ Estado sem 'metricas' para {ativo}")
#         #     except Exception as e:
#         #         print(f"❌ Erro ao calibrar: {e}")
#         #         import traceback
#         #         traceback.print_exc()
#         # else:
#         #     print(f"⚠️ Estado não encontrado para {ativo}")



#         # ============================================
#         # ✅ 3. CALIBRAR REDE NEURAL (CORRIGIDO!)
#         # ============================================
#         if ia_estado:
#             try:
#                 # A função registrar_resultado já converte string JSON para dict automaticamente!
#                 rede.registrar_resultado(ia_estado, lucro_percentual)
#                 print(f"✅ Rede calibrada com lucro: {lucro_percentual:.2f}%")
                
#                 # Mostrar estatísticas (com segurança)
#                 try:
#                     stats = rede.get_estatisticas()
#                     if stats and isinstance(stats, dict):
#                         print("📊 Estatísticas da rede:")
#                         if 'total_operacoes' in stats:
#                             print(f"   Total: {stats['total_operacoes']}")
#                         if 'taxa_acerto' in stats:
#                             print(f"   Taxa de acerto: {stats['taxa_acerto']:.1f}%")
#                         if 'lucro_medio' in stats:
#                             print(f"   Lucro médio: {stats['lucro_medio']:.2f}%")
#                         if 'lucro_total' in stats:
#                             print(f"   Lucro total: {stats['lucro_total']:.2f}")
#                         if 'maior_lucro' in stats:
#                             print(f"   Maior lucro: {stats['maior_lucro']:.2f}")
#                         if 'maior_prejuizo' in stats:
#                             print(f"   Maior prejuízo: {stats['maior_prejuizo']:.2f}")
#                 except Exception as e_stats:
#                     print(f"⚠️ Erro ao obter estatísticas: {e_stats}")
                    
#             except Exception as e:
#                 print(f"❌ Erro ao calibrar rede: {e}")
#                 import traceback
#                 traceback.print_exc()
#         else:
#             print(f"⚠️ Estado não encontrado para {ativo} - pulando calibração")



#         # if ia_estado:
#         #     try:
#         #         # 🔥 CONVERTER string JSON para dict se necessário
#         #         if isinstance(ia_estado, str):
#         #             try:
#         #                 estado_dict = json.loads(ia_estado)
#         #                 print(f"✅ Estado convertido de string para dict")
#         #             except json.JSONDecodeError as e:
#         #                 print(f"⚠️ Erro ao decodificar JSON: {e}")
#         #                 estado_dict = None
#         #         else:
#         #             estado_dict = ia_estado
                
#         #         # Verificar se tem 'metricas'
#         #         if estado_dict and isinstance(estado_dict, dict) and 'metricas' in estado_dict:
#         #             recompensa = rede.registrar_resultado(estado_dict, lucro_percentual)
#         #             print(f"✅ Rede calibrada: {recompensa:.2f}")
                    
#         #             # Mostrar estatísticas
#         #             stats = rede.get_estatisticas()
#         #             print(f"📊 Taxa de acerto: {stats['taxa_acerto']:.1f}%")
#         #             print(f"   Total: {stats['total_operacoes']}")
#         #         else:
#         #             print(f"⚠️ Estado sem 'metricas' para {ativo}")
#         #             if estado_dict and isinstance(estado_dict, dict):
#         #                 print(f"   Chaves disponíveis: {list(estado_dict.keys())}")
#         #     except Exception as e:
#         #         print(f"❌ Erro ao calibrar: {e}")
#         #         import traceback
#         #         traceback.print_exc()
#         # else:
#         #     print(f"⚠️ Estado não encontrado para {ativo}")    

#         # ============================================
#         # ✅ 4. SALVAR EM FINALIZADOS
#         # ============================================
#         op_id = str(uuid.uuid4())
#         FINALIZADOS[op_id] = {
#             "ativo": ativo,
#             "entrada": entrada,
#             "qtd": qtd,
#             "tipo": tipo,
#             "r_fim": round(resultado_final, 2),
#             "mini_stop_pct": mini_stop_pct,
#             "ultimo_status": status_final,
#             "intensidade": intensidade,
#             "historico": historico,
#             "ia_resultado": ia_resultado,
#             "ia_estado": ia_estado,
#             "data_fechamento": datetime.datetime.now().isoformat(),
#             "lucro_percentual": round(lucro_percentual, 2)
#         }

#         # ============================================
#         # ✅ 5. REMOVER DE ATIVOS (DEPOIS DE USAR!)
#         # ============================================
#         ATIVOS.pop(ativo, None)
#         OBSERVAR.pop(ativo, None)
        
#         # ============================================
#         # ✅ 6. SALVAR ARQUIVOS
#         # ============================================
#         salvar_ativos()
#         salvar_finalizados()

#         # ============================================
#         # ✅ 7. ANÁLISE E ATUALIZAÇÃO DA GUI
#         # ============================================
#         if resultado_final >= 0 and MANTER_OBS:
#             adicionar_opcao(ativo)

#         # Converter dicionário para DataFrame
#         df_finalizados = pd.DataFrame.from_dict(FINALIZADOS, orient='index')

#         # Executar análise
#         pior_historico = "*"
#         me_estr, pior_historico = analise_detalhada_alta_intensidade(df_finalizados, limiar_intensidade=52)
#         me_estr2, pior_estr2 = analise_detalhada_alta_intensidade2(df_finalizados, limiar_intensidade=52)
        
#         ANALISE_ESTRATEGIA = str(me_estr2) + "|pior:" + str(pior_estr2)

#         # Atualizar tabela no GUI
#         if tree_finalizados:
#             for item in tree_finalizados.get_children():
#                 tree_finalizados.delete(item)
#             for op_id_f, dados_f in FINALIZADOS.items():
#                 status_tag = "positivo" if dados_f.get("ultimo_status") == "positivo" else "negativo"
#                 tree_finalizados.insert("", "end", values=(
#                     dados_f.get("ativo", ""),
#                     f"{dados_f.get('entrada', 0.0):.2f}",
#                     dados_f.get("qtd", 0.0),
#                     dados_f.get("tipo", ""),
#                     f"{dados_f.get('r_fim', 0.0):.2f}",
#                     dados_f.get("mini_stop_pct", 0.0),
#                     dados_f.get("ultimo_status", ""),
#                     dados_f.get("intensidade", 0.0),
#                     dados_f.get("historico", "")
#                 ), tags=(status_tag,))

#         return resposta


# Cache para análises (evita chamar múltiplas vezes o mesmo ativo)
_cache_analises = {}


def calculate_rsi(series, period=5):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# def sentimento_msg(nivel=0, mensagem=""):
    
#     #contra a alinhada
    
#     if nivel == 0 and ("FORTE" in mensagem or "FRACO" in mensagem):
#         return True
#     if nivel == 1 and ("FORTE" in mensagem or "FRACO" in mensagem) and "contra" not in mensagem :
#         return True
#     elif nivel == 2 and "FRACO" in mensagem :
#         return True
#     elif nivel == 3 and "FRACO" in mensagem and "contra" not in mensagem :
#         return True
#     elif nivel == 4 and "FORTE" in mensagem: 
#         return True
#     elif nivel == 5 and "FORTE" in mensagem and "contra" not in mensagem :
#         return True
    
    
    
    
    
#     return False

def sentimento_msg(nivel=0, mensagem=""):
    match nivel:
        case 0 if "FORTE" in mensagem or "FRACO" in mensagem:
            return True
        case 1 if ("FORTE" in mensagem or "FRACO" in mensagem) and "contra" not in mensagem:
            return True
        case 2 if "FRACO" in mensagem:
            return True
        case 3 if "FRACO" in mensagem and "contra" not in mensagem:
            return True
        case 4 if "FORTE" in mensagem:
            return True
        case 5 if "FORTE" in mensagem and "contra" not in mensagem:
            return True
        case _:
            return False




def obter_analise_completa(ativo):
    """Obtém análise completa (compra e venda) com cache"""
    if ativo in _cache_analises:
        # Verificar se o cache é recente (menos de 5 segundos)
        timestamp, analise_compra, analise_venda = _cache_analises[ativo]
        if time.time() - timestamp < 5:  # 5 segundos de cache
            return analise_compra, analise_venda
    
    # Fazer novas análises
    analise_compra = analise_hibrida_completa(ativo, "compra")
    analise_venda = analise_hibrida_completa(ativo, "venda")
    
    # Armazenar no cache
    _cache_analises[ativo] = (time.time(), analise_compra, analise_venda)
    
    return analise_compra, analise_venda

# Uso:

def analise4_final(ativo, res_antigo, resu_novo, inform):
    # Palavras que indicam que a decisão não deve ser considerada
    palavras_bloqueio = ['BLOQUEAR', 'EVITAR']

    # Dicionário para armazenar as decisões de cada status
    decisoes = {}
    
    for status in ['compra', 'venda']:
        analise = analisar_com_symbolinfo4(
            ativo=ativo,
            status=status,
            resultado_antigo=res_antigo,
            resultado_novo=resu_novo,
            symbol_info=inform
        )
        #decisao2=analise_hibrida_completa(ativo, status)

        decisao = analise['decisao_integrada']['decisao']
        # Verifica se a decisão contém alguma palavra de bloqueio
        bloqueada = any(palavra in decisao for palavra in palavras_bloqueio)
        decisoes[status] = {'decisao': decisao, 'bloqueada': bloqueada}

    # Determina quais status são válidos (não bloqueados)
    compra_valida = not decisoes['compra']['bloqueada']
    venda_valida = not decisoes['venda']['bloqueada']

    # Lógica da decisão final
    if compra_valida and not venda_valida:
        decisao_final = 'compra'
    elif venda_valida and not compra_valida:
        decisao_final = 'venda'
    elif compra_valida and venda_valida:
        # Se ambos são válidos, escolha um (aqui optei por COMPRA, mas pode ajustar)
        decisao_final = 'neutro'   # ou 'VENDA', ou definir outra regra
    else:
        # Ambos bloqueados
        decisao_final = 'neutro'

    return (decisao_final)



def obter_melhor_operacao(ativo):
    """Retorna qual operação tem análise mais favorável"""
    analise_compra, analise_venda = obter_analise_completa(ativo)
    
    if not analise_compra or not analise_venda:
        return "neutro"
    
    # Pontuação das decisões
    pontos = {
        "EXECUTAR_ORDEM": 3,
        "EXECUTAR_COM_CUIDADO": 2,
        "AGUARDAR": 1,
        "EVITAR": 0,
        "BLOQUEAR": -1
    }
    
    pontos_compra = pontos.get(analise_compra.get('decisao_final', ''), 0)
    pontos_venda = pontos.get(analise_venda.get('decisao_final', ''), 0)
    
    # Considerar também a pontuação do book
    if 'analise_book' in analise_compra:
        pontos_compra += analise_compra['analise_book']['classificacao_book'].get('pontuacao_total', 0) / 10
    
    if 'analise_book' in analise_venda:
        pontos_venda += analise_venda['analise_book']['classificacao_book'].get('pontuacao_total', 0) / 10
    
    # Decidir
    if pontos_compra > pontos_venda and pontos_compra >= 3:
        return "compra"
    elif pontos_venda > pontos_compra and pontos_venda >= 3:
        return "venda"
    else:
        return "neutro"


def analise_detalhada_alta_intensidade2(df, limiar_intensidade=55):
    """Análise detalhada - retorna apenas nomes do melhor e pior histórico"""
    
    df_alta = df[df['intensidade'] >= limiar_intensidade].copy()
    
    if df_alta.empty:
        return None, None
    
    # Calcular estatísticas por histórico
    analises = []
    
    for historico in df_alta['historico'].unique():
        df_hist = df_alta[df_alta['historico'] == historico]
        
        # Estatísticas
        total_ops = len(df_hist)
        ops_lucrativas = len(df_hist[df_hist['r_fim'] > 0])
        ops_prejuizo = len(df_hist[df_hist['r_fim'] <= 0])
        media_retorno = df_hist['r_fim'].mean()
        taxa_acerto = ops_lucrativas / total_ops if total_ops > 0 else 0
        
        analises.append({
            'historico': historico,
            'total_ops': total_ops,
            'ops_lucrativas': ops_lucrativas,
            'ops_prejuizo': ops_prejuizo,
            'taxa_acerto': taxa_acerto,
            'media_retorno': media_retorno
        })
    
    # Ordenação por prioridade:
    # 1. Maior número de operações lucrativas (r_fim > 0)
    # 2. Em caso de empate: maior taxa de acerto
    # 3. Em caso de empate: maior média de retorno
    analises_ordenadas = sorted(analises, 
                                key=lambda x: (x['ops_lucrativas'], x['taxa_acerto'], x['media_retorno']),
                                reverse=True)
    
    if not analises_ordenadas:
        return None, None
    
    # Melhor = primeiro da lista ordenada
    # Pior = último da lista ordenada
    melhor = analises_ordenadas[0]['historico']
    pior = analises_ordenadas[-1]['historico']
    
    return melhor, pior


def analise_detalhada_alta_intensidade(df, limiar_intensidade=55):
    """Análise detalhada - retorna apenas nomes do melhor e pior histórico"""
    
    df_alta = df[df['intensidade'] >= limiar_intensidade].copy()
    
    if df_alta.empty:
        return None, None
    
    # Calcular média por histórico
    medias = df_alta.groupby('historico')['r_fim'].mean().sort_values(ascending=False)
    
    if medias.empty:
        return None, None
    
    # Melhor = maior média, Pior = menor média
    melhor = medias.index[0]  # Primeiro
    pior = medias.index[-1]   # Último
    
    print(f"Intensidade >= {limiar_intensidade}:")
    print(f"  Melhor: {melhor} (média: {medias.iloc[0]:.2f})")
    print(f"  Pior: {pior} (média: {medias.iloc[-1]:.2f})")
    
    return melhor, pior





def atualizar_ticker(ticker, status, data=None):
    if ticker not in tickers_STATUS:
        tickers_STATUS[ticker] = {}
    tickers_STATUS[ticker]["status"] = status
    if data:
        tickers_STATUS[ticker]["ultima_atualizacao"] = data

# Exemplo de uso




   









def filtrar_mensagens_textpath():
    """
    Lê o arquivo TEXT_PATH e retorna apenas as mensagens
    que mencionam os 4 primeiros caracteres de ativos salvos
    OU as palavras especiais 'HULL' ou 'CAVEIRA'.
    """
    global ALERTA_ATUAL, ATIVO_COM_ALERTA, NOVA_MSG ,tickers_STATUS 

    avisos = ["HULL", "CAVEIRA","CAVEIRA_P*" ,"FECHAR OPERACAO","BAIXO", "CIMA" ,"MUDOU","RETORNOU" ,"QUEBROU SUPORTE","QUEBROU RESISTENCIA", "T^" ,"LV"] #resetar nesse?"QUEBROU",
    setas=[ "T^" , "LV", "Lv", "(Lv)" ]
    mi_tend= ["CIMA", "BAIXO",  "SUPORTE","RESISTENCIA" ]
    #testar pegar a frase toda apos a palavra caveira

    mensagens_filtradas = []
    try:
        if os.path.exists(TEXT_PATH):
            with open(TEXT_PATH, "r", encoding="utf-8") as f:
                linhas = f.readlines()

            
                
                # verifica ativos (prefixo de 4 caracteres)
            for linha in linhas:
                linha_original = linha.strip()          # mantém a formatação original
                texto = linha_original.upper()

                
                #texto = linha.strip().upper()
                incluir = False

                
                NOVA_MSG=texto
                #print (f"\n------{len(texto)}----------------\n",texto)
               # verifica ativos (prefixo de 4 caracteres)
                #if NOVA_MSG=="": print ("sem mensagens") 
                for ativo in MAPA_ATIVOS.keys():
                    prefixo = ativo.upper()[:4]
                    
                
                
                #for ativo in OBSERVAR.keys():
                #    prefixo = ativo.upper()[:4]
                    
                
                #for ativo in ATIVOS.keys():
                #    prefixo = ativo.upper()[:4]
                #    print ("prefixo:", prefixo)

                    if prefixo in texto:
                        incluir = True
                        # verifica se algum aviso está presente junto do ativo
                        if CAPTAR_OPCAO:                   
                            localizar_e_adicionar(texto,prefixo)
                            #print( f"Linha altrada{prefixo}" ,texto)
                        # Inicializa dicionário para esse prefixo se não existir
                    
                    if re.search(rf'{prefixo}\d', texto):   # <-- ALTERAÇÃO AQUI
                        #print (f"LInha oroginal{prefixo}",linha_original)    
                        #NOVA_MSG=linha_original
                    #if prefixo in texto:
                        incluir = True
                        # verifica se algum aviso está presente junto do ativo
                        if CAPTAR_OPCAO:                   
                            localizar_e_adicionar(texto,prefixo)
                        # Inicializa dicionário para esse prefixo se não existir
                        if prefixo not in tickers_STATUS:
                            tickers_STATUS[prefixo] = {}
                            

                        # --- 3. NOVO: Verifica texto entre colchetes [ ... ] ---
                        match_bracket = re.search(r'\[(.*?)\]', linha_original)
                        if match_bracket:
                            texto_entre_colchetes = match_bracket.group(1)
                            tickers_STATUS[prefixo]["bracket"] = texto_entre_colchetes
                            # Se desejar tratar o conteúdo como seta, você pode adicionar aqui:
                            #if texto_entre_colchetes.upper() in setas:
                            #    for seta in setas:    
                            #        if seta in texto_entre_colchetes.upper():
                            #            
                            # tickers_STATUS[prefixo]["seta"] = seta
                            #else:
                            #    tickers_STATUS[prefixo].pop("seta", None)  
                            # Normaliza a lista de setas para maiúsculas apenas para comparação
                            setas_upper = [s.upper() for s in setas]

                            # Converte o texto do bracket para maiúsculas para a busca
                            bracket_upper = texto_entre_colchetes.upper()

                            # Procura a primeira seta que aparece dentro do bracket
                            seta_encontrada = None
                            for seta_original, seta_upper in zip(setas, setas_upper):
                                if seta_upper in bracket_upper:
                                    #seta_encontrada = seta_original   # mantém o formato original (ex: "(Lv)")
                                    seta_encontrada = seta_upper
                                    break

                            if seta_encontrada:
                                tickers_STATUS[prefixo]["seta"] = seta_encontrada
                            else:
                                # Se não encontrou nenhuma seta, decide se remove a chave ou mantém a anterior
                                # Opção 1: mantém a seta antiga (não faz nada)
                                
                                # Opção 2: remove a seta antiga
                                tickers_STATUS[prefixo].pop("seta", None)
                        
                            """ if texto_entre_colchetes.upper() in setas:
                                tickers_STATUS[prefixo]["seta"] = texto_entre_colchetes.upper()
                                print (f"aqui o texto {texto_entre_colchetes}")
                            else:
                                tickers_STATUS[prefixo].pop("seta", None) """
                        
                        
                        #Mudei aqui para ver se matem em fechar operacao
                        #else:
                            # Opcional: remove a chave se não houver brackets
                        #    tickers_STATUS[prefixo].pop("bracket", None)    



                         # --- 1. Processa avisos (status) ---
                        aviso_encontrado = None
                        numero=None
                        for aviso in avisos:
                            if aviso in texto:
                                aviso_encontrado = aviso
                                print (texto)
                                padrao = rf'{aviso}.*?(\d+)'  # captura o primeiro grupo de dígitos após o aviso
                                match = re.search(padrao, texto)
                                if match:
                                    numero = match.group(1)  # '2' no exemplo
                                print(f"Aviso: {aviso_encontrado}, Número: {numero}")
                                
                                
                                
                                break
                        if aviso_encontrado:
                            ALERTA_ATUAL = aviso_encontrado
                            ATIVO_COM_ALERTA = prefixo
                            # Atualiza status (se não for seta)
                            
                            
                            #terceira_letra= tickers_STATUS[prefixo]["bracket"][2].upper() if bracket and len(bracket) >= 3 else None
                            
                            bracket = tickers_STATUS[prefixo]["bracket"]
                            segunda_letra = bracket[1] if bracket and len(bracket) >= 3 else None
                            terceira_letra = bracket[2] if bracket and len(bracket) >= 3 else None

                            if aviso_encontrado not in setas:
                                tickers_STATUS[prefixo]["status"] = aviso_encontrado
                            #if aviso_encontrado in mi_tend:
                            #    tickers_STATUS[prefixo]["micro_tende"] = aviso_encontrado
                            
                            if ALERTA_ATUAL=="HULL" and terceira_letra in ['G', 'R'] :  
                                tickers_STATUS[prefixo]["micro_tende"] = f"HULL_{terceira_letra}"
                            """ if ALERTA_ATUAL=="CAVEIRA" and terceira_letra in ['G', 'R'] :  
                                tickers_STATUS[prefixo]["micro_tende"] = f"CAVEIRA_{terceira_letra}" """
                            if ALERTA_ATUAL == "CAVEIRA" and numero in (1, 2):    
                                tickers_STATUS[prefixo]["micro_tende"] = f"CAVEIRA_{'G' if numero == 1 else 'R'}"
                            
#condicao_ideal = (primeiro, tipo_opcao.lower() , infoObs.get("seta")) in [('compra', 'call', 'T^' ), ('venda', 'call', 'LV' ) , ('venda', 'put', 'T^'),
                            
                            reset_micro = (tickers_STATUS[prefixo].get("micro_tend"), segunda_letra, terceira_letra) in [    ('HULL_R','g','G'), ('CAVEIRA_R','g','G'),('HULL_R','g','g'), ('CAVEIRA_R','g','g'),
                                                                                                                         ('HULL_G','r','R'), ('CAVEIRA_R','r','R'),('HULL_G','r','r'), ('CAVEIRA_R','r','r')]
                            if reset_micro:
                                tickers_STATUS[prefixo].pop("micro_tend", None) 
                                print("resetrou hull e caveira"*100)
                            #if ALERTA_ATUAL=="CAVEIRA" and tickers_STATUS[prefixo]["bracket"][2].upper() in ['G', 'R'] :  
                            #    tickers_STATUS[prefixo]["micro_tende"] = 'CAVEIRA_', tickers_STATUS[prefixo]["bracket"][2].upper()    

                            # Se o aviso for uma seta, ele também será tratado abaixo, mas não queremos duplicar
                        else:
                            tickers_STATUS[prefixo].pop("status", None)
                            ALERTA_ATUAL = "semm novo alerta!!!"
                        # --- 2. Processa setas (independente) ---
                        """seta_encontrada = None
                        for seta in setas:
                            if seta in texto:
                                seta_encontrada = seta
                                break
                        if seta_encontrada:
                            # Atualiza a chave "seta" (ou "setas") no dicionário
                            
                            #print(f"{seta_encontrada} \n"*100)
                            tickers_STATUS[prefixo]["seta"] = seta_encontrada

                        else:
                            # Opcional: se quiser remover a seta quando não houver, pode usar pop
                            tickers_STATUS[prefixo].pop("seta", None)
                        """                        
                        #break  # já achou o prefixo, não precisa checar outros ativos

                       
                        




                if incluir and linha.strip() not in mensagens_filtradas:
                    mensagens_filtradas.append(linha.strip())
            
        
            # verifica palavras especiais
            if "HULL" in texto or "CAVEIRA" in texto:
                mensagens_filtradas.append(linha.strip())
                
            
    except Exception as e:
        print("⚠️ Erro ao filtrar mensagens:", e)

    return mensagens_filtradas


"""
def filtrar_mensagens_textpath():
   
    global ALERTA_ATUAL, ATIVO_COM_ALERTA, NOVA_MSG, tickers_STATUS

    avisos = ["HULL", "CAVEIRA","CAVEIRA_P*" ,"FECHAR OPERACAO", "MUDOU", "QUEBROU", "T^" ,"?v"] #resetar nesse?
    setas = ["T^" ,"?v"]
    
    mensagens_filtradas = []
    try:
        if os.path.exists(TEXT_PATH):
            with open(TEXT_PATH, "r", encoding="utf-8") as f:
                linhas = f.readlines()

            for linha in linhas:
                texto = linha.strip().upper()
                NOVA_MSG = texto
                incluir = False

                # Verifica ativos (prefixo de 4 caracteres)
                for ativo in ATIVOS.keys():
                    prefixo = ativo.upper()[:4]
                    if prefixo in texto:
                        incluir = True
                        # Captura opção, se necessário
                        if CAPTAR_OPCAO:                   
                            localizar_e_adicionar(texto, prefixo)
                       
                        # Processa os avisos para este ativo
                        for aviso in avisos:
                            if aviso in texto:
                                ALERTA_ATUAL = aviso
                                ATIVO_COM_ALERTA = prefixo

                                # Inicializa dicionário para esse prefixo, se não existir
                                if prefixo not in tickers_STATUS:
                                    tickers_STATUS[prefixo] = {}

                                # Atualiza a chave apropriada sem apagar a outra
                                if aviso in setas:
                                    tickers_STATUS[prefixo]["setas"] = aviso   # ou "seta" se preferir
                                else:
                                    tickers_STATUS[prefixo]["status"] = aviso

                                break   # interrompe o loop dos avisos, pois já achou um
                        else:
                            # Nenhum aviso encontrado para este ativo
                            # (opcional: definir status padrão, se desejar)
                            ALERTA_ATUAL = "semm novo alerta!!!"
                            # Se quiser registrar também:
                            # if prefixo not in tickers_STATUS:
                            #     tickers_STATUS[prefixo] = {}
                            # tickers_STATUS[prefixo]["status"] = ALERTA_ATUAL

                        break   # interrompe o loop dos ativos, pois já achou o prefixo

                # Inclui a mensagem na lista de filtradas se for relevante
                if incluir and linha.strip() not in mensagens_filtradas:
                    mensagens_filtradas.append(linha.strip())
                
                # Verifica palavras especiais (HULL, CAVEIRA) mesmo sem ativo
                # (A indentação original estava incorreta; agora está dentro do loop)
                if "HULL" in texto or "CAVEIRA" in texto:
                    if linha.strip() not in mensagens_filtradas:
                        mensagens_filtradas.append(linha.strip())
            
    except Exception as e:
        print("⚠️ Erro ao filtrar mensagens:", e)

    return mensagens_filtradas"""




def adicionar_opcao(nome_opcao):
    """
    Adiciona uma opção ao dicionário OBSERVAR apenas se a 5ª letra
    ainda não estiver presente em nenhuma chave já existente.
    """
    #book = mt5.market_book_get(nome_opcao)
    #if not book: return
    
    
    if len(nome_opcao) < 5 or len(nome_opcao)>8  :
        return
    
    

    # Verifica se já existe alguma opção com essa 5ª letra
    # if UMA_OPCAO_P_LETRA:
    #     letra_chave = nome_opcao[4].upper()
    #     for existente in OBSERVAR.keys():
    #         if existente[4].upper() == letra_chave:
    #             #print(f"❌ Já existe opção com a 5ª letra '{letra_chave}': {existente}")
    #             return
    if nome_opcao in ATIVOS.keys() or nome_opcao in OBSERVAR.keys():
        #print(f"❌ {nome_opcao} já existe, não será adicionado.")
        return
    preco_atual = preco_medio(nome_opcao)
    prc= preco_real(nome_opcao, "compra")
    prv= preco_real(nome_opcao, "venda")
    prx=prc*prv
    #print(prx, nome_opcao)
    if (nome_opcao in ATIVOS.keys() or nome_opcao in OBSERVAR.keys() 
    or not (MENOR_PRECO_ACEITO <= preco_atual <= MAIOR_PRECO_ACEITO) or prx==0.0 ):
    # ❌ Já existe OU está fora da faixa de preço
        return

    # Se não existe, adiciona normalmente
    OBSERVAR[nome_opcao] = {
        "preco_inicial": preco_atual,
        #"preco_inicial": preco_medio(nome_opcao),
        "status": "indefinido",
        "ultimo_diff": 0.0, "reset":0
    }
    print(f"✅ Adicionado: {nome_opcao}")



def processar_pausa_true(arquivo_json: str):
    """
    Lê o arquivo finalizados.json. Para cada operação cujo histórico contenha 'pausa True',
    chama a função adicionar_opcao(ativo). Não retorna nada.
    """
    try:
        with open(arquivo_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ Arquivo finalizados.json não encontrado ou inválido.")
        return

    for info in dados.values():
        historico = info.get("historico", "")
        if isinstance(historico, str) and "pausa True" in historico:
            ativo = info.get("ativo")
            if ativo and mt5.symbol_info(ativo):
            #if ativo:
                adicionar_opcao(ativo)   # chama sua função existente

processar_pausa_true("finalizados.json")




def localizar_e_adicionar(texto, prefixo):
    """
    Localiza palavras que começam com VALE e adiciona ao dict OBSERVAR.
    """
        
    encontrados = re.findall(fr"\b{prefixo}\w*", texto.upper())
    for opcao in encontrados:
        
        adicionar_opcao(opcao)





# Inicializa MT5
if not mt5.initialize():
    print("❌ Erro ao inicializar MetaTrader 5")
    exit(1)



""" ainda nao usar

def localizar_e_adicionar(texto, prefixo, ativo_principal):

    # checar se temos suporte/resistência calculados para esse ativo
    if ativo_principal not in NIVEIS_ATIVOS:
        return

    suporte = NIVEIS_ATIVOS[ativo_principal]["Suporte1"]
    resistencia = NIVEIS_ATIVOS[ativo_principal]["Resistencia1"]

    # localizar opções no texto
    encontrados = re.findall(fr"\b{prefixo}\w*", texto.upper())
    if not encontrados:
        return

    # obter preço médio de cada opção
    opcoes_precos = {}
    for opcao in encontrados:
        info = mt5.symbol_info(opcao)
        if info and info.bid and info.ask:
            preco = (info.bid + info.ask) / 2
            opcoes_precos[opcao] = preco

    if not opcoes_precos:
        return

    # calcular distância até suporte e resistência
    proximidade = []
    for opcao, preco in opcoes_precos.items():
        dist_suporte = abs(preco - suporte)
        dist_resistencia = abs(preco - resistencia)
        menor_dist = min(dist_suporte, dist_resistencia)
        proximidade.append((opcao, menor_dist))

    # ordenar por proximidade e pegar as 2 mais próximas
    proximidade.sort(key=lambda x: x[1])
    selecionadas = [opcao for opcao, _ in proximidade[:2]]

    # enviar para função secundária
    for opcao in selecionadas:
        adicionar_opcao(opcao)


"""


def suporte_resistencia_diaria(ativo_principal):
    """
    Calcula suporte e resistência diária usando Pivot Points
    com base nos dados do dia anterior.
    """

    try:
        # obtém 2 candles diários: hoje e ontem
        rates = mt5.copy_rates_from_pos(ativo_principal, mt5.TIMEFRAME_D1, 0, 2)
        if rates is None or len(rates) < 2:
            return None

        # dados do dia anterior
        ontem = rates[1]
        alta = ontem['high']
        baixa = ontem['low']
        fechamento = ontem['close']

        # cálculo do pivot point
        pp = (alta + baixa + fechamento) / 3

        # resistências
        r1 = (2 * pp) - baixa
        r2 = pp + (alta - baixa)

        # suportes
        s1 = (2 * pp) - alta
        s2 = pp - (alta - baixa)

        niveis = {
            "Pivot": round(pp, 2),
            "Resistencia1": round(r1, 2),
            "Resistencia2": round(r2, 2),
            "Suporte1": round(s1, 2),
            "Suporte2": round(s2, 2),
        }

        return niveis

    except Exception as e:
        print(f"⚠️ Falha ao calcular suporte/resistência para {ativo_principal}: {e}")
        return None



"""
def atualizar_suporte_resistencia(ativo_principal):
    niveis = suporte_resistencia_diaria(ativo_principal)
    if niveis:
        NIVEIS_ATIVOS[ativo_principal] = niveis
        print(f"🔄 {ativo_principal} atualizado: {niveis}")
"""


def atualizar_suporte_resistencia(ativo_principal, texto, prefixo):
    
    niveis = suporte_resistencia_diaria(ativo_principal)
    if not niveis:
        return

    # pegar valores antigos
    antigo = NIVEIS_ATIVOS.get(ativo_principal)

    # atualizar dict global
    NIVEIS_ATIVOS[ativo_principal] = niveis

    # se houve mudança em suporte ou resistência, dispara verificação
    if not antigo or antigo["Suporte1"] != niveis["Suporte1"] or antigo["Resistencia1"] != niveis["Resistencia1"]:
        print(f"🔄 {ativo_principal} atualizado: S={niveis['Suporte1']} | R={niveis['Resistencia1']}")
        localizar_e_adicionar(texto, prefixo, ativo_principal)





# Função para enviar mensagem ou imagem
async def enviar_telegram(texto, foto_path="", chat_id=CHAT_ID_DEFAULT):
    
    #liberadas= ["STOP", "ENCERRADA", "HULL", "CAVEIRA", "registrada"]
    #for liberada in liberadas:
    #    if liberada not in texto and APENAS_MSGS_STOP:
    #        return
    
    liberadas = ["STOP", "ENCERRADA", "HULL", "CAVEIRA", "registrada", "Filtro", "Mini", "Stop","Comandos", "ativos", "Observando", "mudou" ]

    # regra de envio
    if foto_path=="":
        if APENAS_MSGS_STOP and not any(palavra in texto for palavra in liberadas) :
            return  # não envia nada
    
    #if "STOP" not in texto and APENAS_MSGS_STOP:
        # não envia nada
    #    return
        agora= time.time()

    # se já foi enviado e ainda está dentro do intervalo, não envia
        if texto in mensagens_enviadas and (agora - mensagens_enviadas[texto]) < INTERVALO_BLOQUEIO:
            return

    # registra envio
        mensagens_enviadas[texto] = agora
    
    async with httpx.AsyncClient() as client:
        try:
            if foto_path == "":
                #if "STOP" not in texto and APENAS_MSGS_STOP:                                
                    #await client.post(BASE_URL + "sendMessage", data={"chat_id": chat_id, "text": texto})
                #    return
                #else:
                #    await client.post(BASE_URL + "sendMessage", data={"chat_id": chat_id, "text": texto})
                
                await client.post(BASE_URL + "sendMessage", data={"chat_id": chat_id, "text": texto})
                
            else:
                with open(foto_path, "rb") as f:
                    files = {"photo": f}
                    data = {"chat_id": chat_id, "caption": texto}
                    await client.post(BASE_URL + "sendPhoto", data=data, files=files)
        except Exception as e:
            pass
            #print("⚠️ Erro ao enviar mensagem:", e)


# def ativo_principal(opcao):
#     prefixo = opcao[:4].upper()
#     if prefixo in MAPA_ATIVOS:
#         return MAPA_ATIVOS[prefixo]
#     sufixos_possiveis = ["3", "4", "5", "6"]
#     for suf in sufixos_possiveis:
#         candidato = prefixo + suf
#         info = mt5.symbol_info(candidato)
#         if info is not None:
#             MAPA_ATIVOS[prefixo] = candidato
#             return candidato
#     MAPA_ATIVOS[prefixo] = None
#     return None

# def ativo_principal(opcao):
#     ativo = opcao.upper().strip()
#     # 1. Se o ativo já for um principal (termina com 3,4,5,6 e existe no MT5)
#     if ativo[5]  in ["3", "4", "5", "6"] and mt5.symbol_info(ativo) is not None:
#         # (Opcional) Armazena no cache para consultas futuras
#         # Se quiser, pode fazer: MAPA_ATIVOS[ativo[:4]] = ativo
#         return ativo
#     # 2. Caso contrário, aplica a lógica original
#     prefixo = ativo[:4].upper()
#     # Verifica se já temos mapeamento para esse prefixo
#     if prefixo in MAPA_ATIVOS:
#         return MAPA_ATIVOS[prefixo]
    
#     # Tenta cada sufixo possível
#     sufixos_possiveis = ["3", "4", "5", "6"]
#     for suf in sufixos_possiveis:
#         candidato = prefixo + suf
#         if mt5.symbol_info(candidato) is not None:
#             MAPA_ATIVOS[prefixo] = candidato
#             return candidato
    
#     # Nenhum encontrado
#     MAPA_ATIVOS[prefixo] = None
#     return None
def ativo_principal(opcao):
    # Extrai sempre os 4 primeiros caracteres como prefixo
    prefixo = opcao[:4].upper()
    
    # Verifica cache
    if prefixo in MAPA_ATIVOS:
        return MAPA_ATIVOS[prefixo]
    
    # Tenta os sufixos canônicos
    for suf in ["3", "4", "5", "6"]:
        candidato = prefixo + suf
        if mt5.symbol_info(candidato) is not None:
            MAPA_ATIVOS[prefixo] = candidato
            return candidato
    
    # Não encontrou
    MAPA_ATIVOS[prefixo] = None
    return None


# def ativo_principal(opcao):
#     # Extrai sempre os 4 primeiros caracteres como prefixo
#     prefixo = opcao[:4].upper()
    
#     # Verifica se já temos mapeamento para esse prefixo
#     if prefixo in MAPA_ATIVOS:
#         return MAPA_ATIVOS[prefixo]
    
#     # Tenta cada sufixo possível (3,4,5,6)
#     sufixos_possiveis = ["3", "4", "5", "6"]
#     for suf in sufixos_possiveis:
#         candidato = prefixo + suf
#         if mt5.symbol_info(candidato) is not None:
#             MAPA_ATIVOS[prefixo] = candidato
#             return candidato
    
#     # Nenhum encontrado
#     MAPA_ATIVOS[prefixo] = None
#     return None






def tipo_op(ativo):
    # --- 3. Identificar tipo da opção (CALL ou PUT) pela 5ª letra ---
    tipo_opcao = ativo[4].upper() if len(ativo) > 4 else ""
    status = "CALL" if tipo_opcao in "ABCDEFGHIJKL" else ("PUT" if tipo_opcao in "MNOPQRSTUVWXYZ"  else "ACAO")
        
    
    return status 


# def gap_venda(ativo):
#     symbol = ativo_principal( ativo)
    
#     tick = mt5.symbol_info_tick(symbol)
#     if tick:
#         #preco_principal = (tick.ask + tick.bid) / 2.0
#         ultima_venda= tick.last
#         gap_venda=   ultima_venda - tick.ask
        
        
        
#         #status1 = "compra" if diff >= GATILHO_DIFF_PRECO else ("venda" if diff <= -GATILHO_DIFF_PRECO else "neutro")
#         saida= "sobe" if gap_venda>0 else ("desce" if gap_venda< 0 else "neutro" ) 
#         saida=  f"{saida, { gap_venda}}"
#         return saida

def gap_venda(ativo):
    symbol = ativo_principal(ativo)   # sua função, precisa existir
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    
    last = tick.last
    ask = tick.ask
    gap_abs = last - ask                # pode ser positivo ou negativo
    gap_pct = (gap_abs / ask) * 100     # percentual relativo ao ask
    
    # Classificação mais intuitiva
    if gap_abs > 0:
        status = "acima_ask queda"   # last > ask (negócio executado acima da oferta)
    elif gap_abs < 0:
        status = "abaixo_ask alta "  # last < ask (normal, last está abaixo do ask)
    else:
        status = "igual_ask  "
    
    return {
        # "ativo": symbol,
        # "last": last,
        # "ask": ask,
        # "gap_absoluto": gap_abs,
        # "gap_percentual": gap_pct,
        "status": status
    }


#............trailing stop

#....................


def analise_pressao_preco(ativo, mesmo ):
    """
    Analisa a pressão compradora/vendedora baseada na relação entre last, bid e ask.
    Retorna um dicionário com indicadores e uma sugestão de direção.
    """
    
    if mesmo == True: 
        symbol = ativo 
    else:    
        symbol = ativo_principal(ativo)
    
    # Garantir que o símbolo está visível no Market Watch
    if not mt5.symbol_select(symbol, True):
        print(f"Símbolo {symbol} não encontrado ou não selecionado")
        return None
    
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Não foi possível obter tick para {symbol}")
        return None
    
    last = tick.last
    bid = tick.bid
    ask = tick.ask
    
    # Cálculo dos gaps
    gap_ask = last - ask
    gap_bid = last - bid
    gap_ask_pct = (gap_ask / ask) * 100 if ask != 0 else 0
    gap_bid_pct = (gap_bid / bid) * 100 if bid != 0 else 0
    
    # Lógica de direção
    # if last > ask:
    #     direcao = "ALTA"
    #     forca = "forte" if gap_ask > (ask * 0.001) else "moderada"  # 0.1% de threshold
    # elif last < bid:
    #     direcao = "QUEDA"
    #     forca = "forte" if abs(gap_bid) > (bid * 0.001) else "moderada"
    # else:
    #     direcao = "NEUTRO"
    #     forca = "sem pressão"
    
    if last > ask:
        direcao = "QUEDA"
        forca = "forte" if gap_ask > (ask * 0.001) else "moderada"  # 0.1% de threshold
        
    
    elif last < ask:
        direcao = "ALTA"
        forca = "forte" if abs(gap_bid) > (bid * 0.001) else "moderada"
    
    elif last < bid:
        direcao = "QUEDA"
        forca = "forte" if gap_ask > (ask * 0.001) else "moderada"
    else:
        direcao = "NEUTRO"
        forca = "sem pressão"
    



    resultado = {
        #"ativo": symbol,
        #"last": last,
        #"bid": bid,
        #"ask": ask,
        #"spread": ask - bid,
        #"gap_ask_abs": gap_ask,
        #"gap_ask_pct": gap_ask_pct,
        #"gap_bid_abs": gap_bid,
        #"gap_bid_pct": gap_bid_pct,
        "direcao": direcao,
        "forca": forca,
        "status_ask": "acima_ask" if last > ask else ("abaixo_ask" if last < ask else "igual_ask"),
        "status_bid": "acima_bid" if last > bid else ("abaixo_bid" if last < bid else "igual_bid")
    }
    
    return resultado







# def expectativa_precos(ativo, mesmo=True, threshold=0.001):
#     symbol = ativo if mesmo else ativo_principal(ativo)
    
#     if not mt5.symbol_select(symbol, True):
#         print(f"Símbolo {symbol} não encontrado ou não selecionado")
#         return None
    
#     tick = mt5.symbol_info_tick(symbol)
#     if tick is None:
#         print(f"Não foi possível obter tick para {symbol}")
#         return None
    
#     last, bid, ask = tick.last, tick.bid, tick.ask
    
#     # Expectativa baseada na posição do last
#     if ask > last:
#         expectativa = "VALORIZA"
#         intensidade = "forte" if (ask - last) > (last * threshold) else "moderada"
#     elif bid < last:
#         expectativa = "QUEDA"
#         intensidade = "forte" if (last - bid) > (last * threshold) else "moderada"
#     else:
#         expectativa = "NEUTRO"
#         intensidade = "sem expectativa clara"
    
#     resultado = {
#         "ativo": symbol,
#         "last": last,
#         "bid": bid,
#         "ask": ask,
#         "spread": ask - bid,
#         "expectativa": expectativa,
#         "intensidade": intensidade,
#         "status_ask": "ask acima do last" if ask > last else "ask abaixo/igual ao last",
#         "status_bid": "bid abaixo do last" if bid < last else "bid acima/igual ao last"
#     }
    
#     return resultado


# def expectativa_precos_com_book(ativo, threshold=0.001):
#     """
#     Analisa expectativa de valorização ou queda com base em:
#     - relação entre last, bid e ask
#     - balanço de compradores vs vendedores no book
#     """
#     if not mt5.symbol_select(ativo, True):
#         print(f"Símbolo {ativo} não encontrado ou não selecionado")
#         return None
    
#     tick = mt5.symbol_info_tick(ativo)
#     if tick is None:
#         print(f"Não foi possível obter tick para {ativo}")
#         return None
    
#     last, bid, ask = tick.last, tick.bid, tick.ask
#     compradores, vendedores = compradores_vendedores(ativo)
    
#     # Expectativa baseada em preços
#     if ask > last:
#         expectativa = "VALORIZAÇÃO"
#         intensidade = "forte" if (ask - last) > (last * threshold) else "moderada"
#     elif bid < last:
#         expectativa = "QUEDA"
#         intensidade = "forte" if (last - bid) > (last * threshold) else "moderada"
#     else:
#         expectativa = "NEUTRO"
#         intensidade = "sem expectativa clara"
    
#     # Ajuste pela força do book
#     if compradores is not None and vendedores is not None:
#         if vendedores > compradores:
#             expectativa += " (pressão vendedora)"
#         elif compradores > vendedores:
#             expectativa += " (pressão compradora)"
#         else:
#             expectativa += " (equilibrado)"
    
#     resultado = {
#         "ativo": ativo,
#         "last": last,
#         "bid": bid,
#         "ask": ask,
#         "spread": ask - bid,
#         "expectativa": expectativa,
#         "intensidade": intensidade,
#         "compradores": compradores,
#         "vendedores": vendedores,
#         "status_ask": "ask acima do last" if ask > last else "ask abaixo/igual ao last",
#         "status_bid": "bid abaixo do last" if bid < last else "bid acima/igual ao last"
#     }
    
#     return resultado



def expectativa_precos(ativo,mesmo=True ,threshold=0.001):
    
    tipo =tipo_op(ativo)
    symbol = ativo if mesmo else ativo_principal(ativo)
    expectativa="NEUTRO"
    forca=""
    intensidade=""
    if not mt5.symbol_select(symbol, True):
        print(f"Símbolo {symbol} não encontrado ou não selecionado")
        return None
    
    tick = mt5.symbol_info_tick(symbol)
   
    if tick is None:
        print(f"Não foi possível obter tick para {symbol}")
        return None

     # --- Capturar close de 1 minuto atrás ---
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 1, 2)
    if rates is not None and len(rates) > 0:
        close_ref = rates[0]['close']   # preço de fechamento do candle anterior (1 min atrás)
        open1 = rates[0]['open']
        low1  = rates[0]['low']
        hig1= rates[0]['high']

        close2 = rates[1]['close']   # preço de fechamento do candle anterior (1 min atrás)
        open2 = rates[1]['open']
        low2  = rates[1]['low']
        hig2= rates[1]['high']
    
    else:
        close_ref = None
        print(f"Erro ao obter close de 1 min atrás para {symbol}")
            
    
    last, bid, ask = tick.last, tick.bid, tick.ask
    if tipo != "PUT":
        compradores, vendedores = compradores_vendedores(ativo_principal(ativo))
    else:  vendedores, compradores = compradores_vendedores(ativo_principal(ativo))  
    
    mid = (ask + bid) / 2
    gap =0
    gap_ask = last - ask
    gap_bid = last - bid
    gap = gap_preco_real( ativo_principal(ativo) )

    if vendedores is not None:
        gap = -gap if vendedores < compradores else gap

    if close_ref is None:
           close_ref = last  # fallback

    #condicao_up = (open1 > close_ref) and (low1 < open1) and (open0 < last) and (last > open1)
    #condicao_down = (open1 < close_ref) and (hig1>close_ref ) and (open0 > last) and (last < open1)
    
    
    if compradores is not None and vendedores is not None:
    
        if last>close_ref:
            if last < mid :  #and compradores > vendedores:
                expectativa = "ALTA" if mid > close_ref else "alta-"
                intensidade = "forte" if compradores> vendedores else "fraca"
            elif bid > last and compradores > vendedores :
                expectativa = "ALTA"
                intensidade = "moderada"
            elif bid < last and compradores > vendedores :
                expectativa = "ALTA"
                intensidade = "moderada"   
            elif last < mid and compradores > vendedores :
                expectativa = "ALTA"
                intensidade = "moderada"
            elif ask > last and compradores > vendedores :
                expectativa = "ALTA"
                intensidade = "forte" if (ask - last) > (last * threshold) else "moderada"

        elif last<close_ref:
            if last > mid :
                expectativa = "QUEDA" if mid < close_ref else "queda-"
                intensidade = "forte" if  vendedores > compradores else "fraca" #"forte" if (last - bid) > (last * threshold) else "moderada"    
            elif last > ask and vendedores > compradores :
                expectativa = "QUEDA"
                intensidade = "forte" 
            elif last > ask and compradores > vendedores :
                expectativa = "QUEDA"
                intensidade = "forte" 
            elif ask > last and vendedores > compradores :
                expectativa = "QUEDA"
                intensidade = "forte" if (ask - last) > (last * threshold) else "moderada"
            elif ask > last and compradores > vendedores :
                expectativa = "ALTA"
                intensidade = "forte" if (ask - last) > (last * threshold) else "moderada"
    
            elif bid < last and vendedores > compradores :
                expectativa = "QUEDA"
                intensidade = "forte" if (last - bid) > (last * threshold) else "moderada" 
                   
            # elif last > mid :
            #     expectativa = "QUEDA"
            #     intensidade = "forte" if (last - bid) > (last * threshold) else "moderada"

        else:
            expectativa = f"NEUTRO"
            intensidade = "sem expectativa clara"

         
                     


    resultado = {
        "ativo": ativo,
        "last": last,
        "bid": bid,
        "ask": ask,
        "gap":gap,
        "spread": ask - bid,
        "expectativa": expectativa,
        "intensidade": intensidade,
        "compradores": compradores,
        "vendedores": vendedores,
        "status_ask": "ask acima do last" if ask > last else "ask abaixo/igual ao last",
        "status_bid": "bid abaixo do last" if bid < last else "bid acima/igual ao last"
    }
    
    return resultado




"""
ult_venda= SymbolInfoDouble(ativo, SYMBOL_LAST);
      g= max_venda-max_compra;
      gv= MathAbs(max_venda-ult_venda);
      gap= (g>0.02)?"G"+DoubleToString(g,2) :"";
      media = (max_compra+max_venda)/2;
      /*string pr= (max_venda > ult_venda && max_compra> ult_venda)?"^^":(max_venda > ult_venda)?"^":
               (max_venda < ult_venda && max_compra < ult_venda)?"vv": (max_venda < ult_venda)?"v":"-";
      */
      string pr= (max_venda > ult_venda && max_compra> ult_venda && volum_compra>volum_venda)?"^^":
                 (max_venda > ult_venda && volum_compra>volum_venda)?"^":
                 (max_venda < ult_venda && max_compra < ult_venda &&volum_compra<volum_venda)?"vv":
                 (max_venda < ult_venda && volum_compra<volum_venda)?"v":"-";

      vai= (max_venda > ult_venda && max_compra> ult_venda) || (max_venda < ult_venda && max_compra < ult_venda)   ?"*":"";

      vai+=pr;
      previsao= (priceArray[size/2].volume>priceArray[(size/2)-1 ].volume)? vai+"▲"+vai+gap :
                (priceArray[size/2].volume<priceArray[(size/2)-1 ].volume)?vai+"▼"+vai+gap: "_"  ;




"""







def compradores_vendedores(ativo):
    try:
        book = mt5.market_book_get(ativo)
        if book:
            compradores = sum(b.volume for b in book if b.type == mt5.BOOK_TYPE_BUY)
            vendedores = sum(b.volume for b in book if b.type == mt5.BOOK_TYPE_SELL)
            return compradores, vendedores
    except Exception as e:
        print(f"⚠️ MT5 book falhou para {ativo}:", e)
    return None, None

def intensidade_sinal_antiga(ativo, status, limiar=LIMIAR_FORCA):
    """
    Calcula a intensidade de um sinal de compra ou venda para opções,
    combinando dados do book da opção e do ativo principal.

    Args:
        ativo (str): Código do ativo (ex: "VALE3H24").
        status (str): "compra" ou "venda".
        limiar (float): Limiar percentual para considerar o sinal forte (ex: 60).

    Returns:
        tuple: (mensagem_formatada, percentual_combinado, percentual_principal)
    """
    try:
        # --- 1. Obter book da opção ---
        book_opcao = mt5.market_book_get(ativo)
        comp_opcao = 0
        vend_opcao = 0
        if book_opcao:
            comp_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_BUY)
            vend_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_SELL)

        # --- 2. Obter dados do ativo principal ---
        principal = ativo_principal(ativo)  # função externa que extrai o ativo-objeto
        comp_princ = vend_princ = 0
        preco_principal = None
        tick = None

        if principal:
            book_princ = mt5.market_book_get(principal)
            if book_princ:
                comp_princ = sum(b.volume for b in book_princ if b.type == mt5.BOOK_TYPE_BUY)
                vend_princ = sum(b.volume for b in book_princ if b.type == mt5.BOOK_TYPE_SELL)

            tick = mt5.symbol_info_tick(principal)
            if tick:
                preco_principal = (tick.ask + tick.bid) / 2.0

        # --- 3. Identificar tipo da opção (CALL ou PUT) pela 5ª letra ---
        tipo_opcao = ativo[4].upper() if len(ativo) > 4 else ""
        is_call = tipo_opcao in "ABCDEFGHIJKL"  # CALLs
        is_put = tipo_opcao in "MNOPQRSTUVWXYZ"  # PUTs

        # --- 4. Definir forças otimista e pessimista conforme o tipo ---
        # Para CALL: otimista = compradores (opção + principal), pessimista = vendedores (opção + principal)
        # Para PUT: otimista = vendedores da opção + compradores do principal, pessimista = compradores da opção + vendedores do principal
        if is_call:
            forca_otimista = comp_opcao + comp_princ
            forca_pessimista = vend_opcao + vend_princ
        elif is_put:
            forca_otimista = vend_opcao + comp_princ
            forca_pessimista = comp_opcao + vend_princ
        else:
            # Se não for possível identificar, trata como CALL (padrão)
            forca_otimista = comp_opcao + comp_princ
            forca_pessimista = vend_opcao + vend_princ

        total = forca_otimista + forca_pessimista
        if total == 0:
            return "DESCONHECIDO", 0.0, 0.0

        # --- 5. Calcular proporção combinada conforme status e tipo ---
        if status.lower() == "compra":
            if is_call:      # comprar CALL = posição otimista
                proporcao = forca_otimista / total
            else:            # comprar PUT = posição pessimista
                proporcao = forca_pessimista / total
        else:  # venda
            if is_call:      # vender CALL = posição pessimista
                proporcao = forca_pessimista / total
            else:            # vender PUT = posição otimista
                proporcao = forca_otimista / total

        # --- 6. Calcular proporção apenas do ativo principal (antes do ajuste) ---
        if comp_princ + vend_princ > 0:
            if status.lower() == "compra":
                prop_princ = comp_princ / (comp_princ + vend_princ)
            else:
                prop_princ = vend_princ / (comp_princ + vend_princ)
        else:
            prop_princ = 0.0

        # --- 7. Ajuste por spread e pressão no ativo principal (após cálculo) ---
        if tick:
            spread = tick.ask - tick.bid
            # Aplica reforço de 5% se spread >= 0.02 e a pressão estiver a favor da posição
            if spread >= 0.02:
                if status.lower() == "venda" and vend_princ > comp_princ:
                    prop_princ = min(1.0, prop_princ + 0.05)
                elif status.lower() == "compra" and comp_princ > vend_princ:
                    prop_princ = min(1.0, prop_princ + 0.05)

        # --- 8. Formatar resultados ---
        percentual = round(proporcao * 100, 1)
        percentual_principal = round(prop_princ * 100, 1)
        intensidade = "FORTE" if percentual >= limiar else "FRACO"

        # --- 9. Gerar mensagem de reforço contextual ---
        ajuste = ""
        if preco_principal:
            if is_call:
                if status.lower() == "compra" and forca_otimista > forca_pessimista:
                    ajuste = "✔️ CALL reforçada pela alta do ativo"
                elif status.lower() == "venda" and forca_pessimista > forca_otimista:
                    ajuste = "✔️ Venda de CALL reforçada pela queda do ativo"
            elif is_put:
                if status.lower() == "compra" and forca_pessimista > forca_otimista:
                    ajuste = "✔️ Compra de PUT reforçada pela queda do ativo"
                elif status.lower() == "venda" and forca_otimista > forca_pessimista:
                    ajuste = "✔️ Venda de PUT reforçada pela alta do ativo"

        mensagem = (
            f"{status.upper()} {intensidade} ({percentual}%)\n"
            f"📊 Força a favor: {int(forca_otimista if (status.lower()=='compra' and is_call) or (status.lower()=='venda' and not is_call) else forca_pessimista)} | Contra: {int(forca_pessimista if (status.lower()=='compra' and is_call) or (status.lower()=='venda' and not is_call) else forca_otimista)}\n"
            f"🔗 Principal usado: {principal if principal else 'nenhum'}\n"
            f"📈 Percentual principal: {percentual_principal}%\n"
            f"{ajuste}"
        )

        return mensagem, percentual, percentual_principal

    except Exception as e:
        print(f"⚠️ Erro na análise para {ativo}:", e)
        return "DESCONHECIDO", 0.0, 0.0




# def determinar_direcao_RSI(opcao):
#     symbol= ativo_principal(opcao)
    
#     symbol = "VALE3"
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
#     # Converter para DataFrame
#     df = pd.DataFrame(rates)
#     close_prices = df['close']
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ma_9 = rsi_5.rolling(9).mean()
#     # Remove valores NaN (primeiros períodos)
#     rsi_5 = rsi_5.dropna()
#     ma_9 = ma_9.dropna()


#     rsi_list = rsi_5.tail(5).tolist()   # ex.: [82.31, 96.24, 96.27]
#     ma_list  = ma_9.tail(5).tolist() #3

    
                    
#     print("\nÚltimos 3 valores do RSI:")
#     print(rsi_5.tail(3), rsi_list[0],"   ATUAL= " , rsi_list[4] )
#     print("\nÚltimos 3 valores da MA do RSI:")
#     print(ma_9.tail(3))

#     cruzamentos = []
#     for i in range(len(rsi_list)-1):
#         if rsi_list[i] < ma_list[i] and rsi_list[i+1] > ma_list[i+1]:
#             cruzamentos.append(f"Alta entre posição {i} e {i+1}")
#         elif rsi_list[i] > ma_list[i] and rsi_list[i+1] < ma_list[i+1]:
#             cruzamentos.append(f"Baixa entre posição {i} e {i+1}")

#     if cruzamentos:
#         print("Cruzamentos nas últimas 3 barras:", cruzamentos)
#     else:
#         print("Nenhum cruzamento nas últimas 3 barras.")

    
#     if rsi_list[4] > ma_list[4]: return ('vai subir')
#     elif rsi_list[4] < ma_list[4]: return('vai descer')
#     else:  
#         return('parado')
    
# def determinar_direcao_RSI(opcao):
#     # Obtém o símbolo (assumindo que ativo_principal está definido)
#     symbol = ativo_principal(opcao)  # ou "VALE3" fixo
#     symbol = "VALE3"
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
#     if rates is None or len(rates) < 50:
#         return "erro", "dados_insuficientes", []

#     df = pd.DataFrame(rates)
#     close_prices = df['close']

#     # Calcula RSI(5) e EMA(9) sobre o RSI (igual ao MODE_EMA do MT5)
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()

#     # Remove valores NaN (primeiros períodos)
#     rsi_5 = rsi_5.dropna()
#     ema_9_rsi = ema_9_rsi.dropna()

#     # Obtém os últimos 5 valores (para análise de tendência)
#     rsi_list = rsi_5.tail(5).tolist()
#     ma_list = ema_9_rsi.tail(5).tolist()

#     if len(rsi_list) < 5:
#         return "dados_insuficientes", "poucos_dados", []

#     # --- 1. Cruzamentos (nas últimas 4 transições entre os 5 pontos) ---
#     cruzamentos = []
#     for i in range(len(rsi_list)-1):
#         if rsi_list[i] < ma_list[i] and rsi_list[i+1] > ma_list[i+1]:
#             cruzamentos.append(f"Alta entre {i} e {i+1}")
#         elif rsi_list[i] > ma_list[i] and rsi_list[i+1] < ma_list[i+1]:
#             cruzamentos.append(f"Baixa entre {i} e {i+1}")

#     # --- 2. Cálculo das diferenças (RSI - MA) e classificação de tendência ---
#     diff_list = [rsi_list[j] - ma_list[j] for j in range(5)]

#     # Calcula as diferenças entre diferenças consecutivas (variações)
#     variacoes = [diff_list[i+1] - diff_list[i] for i in range(4)]

#     if all(v == 0 for v in variacoes):
#         tendencia_diff = "estável"
#     elif all(v > 0 for v in variacoes):
#         tendencia_diff = "crescente"
#     elif all(v < 0 for v in variacoes):
#         tendencia_diff = "decrescente"
#     else:
#         tendencia_diff = "flutuante"

#     # Interpreta o impulso baseado na tendência da diferença e posição atual
#     diff_atual = diff_list[-1]
#     if diff_atual > 0:
#         posicao = "acima_da_MA"
#     elif diff_atual < 0:
#         posicao = "abaixo_da_MA"
#     else:
#         posicao = "neutro"

#     if tendencia_diff == "crescente":
#         if diff_atual < 0:
#             impulso = "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"
#         else:
#             impulso = "ACELERAÇÃO DE ALTA (RSI se afastando para cima)"
#     elif tendencia_diff == "decrescente":
#         if diff_atual > 0:
#             impulso = "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"
#         else:
#             impulso = "ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)"
#     elif tendencia_diff == "estável":
#         impulso = "IMPULSO NEUTRO (diferença constante)"
#     else:
#         impulso = "IMPULSO INDEFINIDO (oscilação sem direção clara)"

#     # --- 3. Direção final (baseada na posição atual) ---
#     rsi_atual = rsi_list[-1]
#     ma_atual = ma_list[-1]

#     if rsi_atual > ma_atual:
#         direcao = "vai subir"
#     elif rsi_atual < ma_atual:
#         direcao = "vai descer"
#     else:
#         direcao = "parado"

#     # Exibição (opcional, pode ser removida)
#     print(f"RSI: {rsi_list}")
#     print(f"MA : {ma_list}")
#     print(f"Diferenças: {[round(d,2) for d in diff_list]}")
#     print(f"Tendência da diferença: {tendencia_diff}")
#     print(f"Impulso: {impulso}")
#     if cruzamentos:
#         print("Cruzamentos:", cruzamentos)
#     else:
#         print("Nenhum cruzamento.")
#     print(f"Direção: {direcao}")

#     return direcao, impulso, cruzamentos, tendencia_diff

# def houve_quebra_lateralizacao(df, n=3, tolerancia=0.002):
#     """
#     df: DataFrame com colunas ['open','close']
#     n: número de velas para considerar como faixa lateral
#     tolerancia: percentual máximo de variação permitido
#     Retorna True se a última vela rompeu a lateralização, senão False
#     """

#     if len(df) < n+1:
#         return False  # não há velas suficientes para análise

#     # pega janela anterior de n velas
#     base = df.iloc[-(n+1):-1]

#     # calcula faixa de preços (open/close)
#     valores = list(base['open']) + list(base['close'])
#     max_val = max(valores)
#     min_val = min(valores)

#     faixa = (max_val - min_val) / max_val
#     lateralizado = faixa <= tolerancia

#     # última vela
#     ultima = df.iloc[-1]
#     rompeu = lateralizado and (ultima['close'] > max_val or ultima['close'] < min_val)

#     return rompeu


def houve_quebra_lateralizacao(df, n=2, tolerancia=0.002):
    """
    Verifica se a última vela rompe uma faixa lateral definida pelas n velas anteriores.
    A última vela NÃO entra no cálculo da faixa.
    """
    if len(df) < n + 1:
        return False

    # Velas que definem a faixa (exclui a última)
    velas_base = df.iloc[-n-1:-1]   # mesmo que anterior, mas mais legível

    # Preços (open e close) das velas base
    precos_base = list(velas_base['open']) + list(velas_base['close'])
    max_base = max(precos_base)
    min_base = min(precos_base)

    # Verifica se o intervalo é lateral
    faixa_relativa = (max_base - min_base) / max_base
    is_lateral = faixa_relativa <= tolerancia

    if not is_lateral:
        return False

    # Última vela (a ser observada)
    ultima = df.iloc[-1]
    rompeu_acima = ultima['close'] > max_base
    rompeu_abaixo = ultima['close'] < min_base

    return True  #rompeu_acima or rompeu_abaixo



def meu_rompeu(df, n=2):    
    if len(df) < n + 1:
        return False
    
    # Velas-base: as n velas imediatamente anteriores à última
    velas_base = df.iloc[-n-1:-1]
    
    #precos_base = pd.concat([velas_base['open'], velas_base['close']])
    #max_base = precos_base.max()
    #min_base = precos_base.min()        

    # Maior e menor preço entre todas as velas-base (high, low e close)
    max_base = max(velas_base['high'].max(), velas_base['close'].max())
    min_base = min(velas_base['low'].min(), velas_base['close'].min())
    
    # Fechamento da última vela
    ultimo_close = df.iloc[-1]['close']
    
    # Verifica rompimento para cima ou para baixo
    return ultimo_close > max_base or ultimo_close < min_base
    
    
    
    # Pega todos os preços de open e close das velas base
    
# def rompimento_saida(opcao,n=1):
#     # Obtém o símbolo
#     symbol = ativo_principal(opcao)
#     #symbol = "VALE3"  # fallback
#     #prefixo = symbol.upper()[:4]
#     # Inicializa dicionário para esse prefixo, se não existir
#     # if prefixo not in tickers_STATUS:
#     #     tickers_STATUS[prefixo] = {}
#     #     tickers_STATUS[prefixo]["trivelas"] = None   
   
#     timeframe = mt5.TIMEFRAME_M1
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 5)
#     acho=None
#     if rates is None or len(rates) < 5:
#         return "erro", "dados_insuficientes", [], "indefinida", "AGUARDAR (dados insuficientes)"
#     else:
#         df = pd.DataFrame(rates)
#         ultimo_close = df.iloc[-1]['close']
#         penultimo_close=df.iloc[-2]['close']
        
#         return f"{penultimo_close} / {ultimo_close}"

# def rompimento_saida(opcao, n=1):
#     symbol = ativo_principal(opcao)
#     timeframe = mt5.TIMEFRAME_M2
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 5)
#     msg_panico = None
#     if rates is None or len(rates) < 5:
#         return msg_panico

#     df = pd.DataFrame(rates)
#     close_atual = df.iloc[-1]['close']      # close1
#     open_atual  = df.iloc[-1]['open']       # open1

#     close_ant = df.iloc[-2]['close']        # close2
#     open_ant  = df.iloc[-2]['open']         # open2
#     high_ant  = df.iloc[-2]['high']         # high2
#     low_ant   = df.iloc[-2]['low']          # low2   (necessário para condição de cima)

    
#     velas_base = df.iloc[-n-1:-1]
#     # Maior e menor preço entre todas as velas-base (high, low e close)
#     max_base = max(velas_base['high'].max(), velas_base['close'].max())
#     min_base = min(velas_base['low'].min(), velas_base['close'].min())
    
#     # Fechamento da última vela
#     ultimo_close = df.iloc[-1]['close']
    
#     # Verifica rompimento para cima ou para baixo
#     rompeu = ultimo_close > max_base or ultimo_close < min_base




#     # Condição de REVERSÃO PARA BAIXO (bearish)
#     if open_ant < close_ant and high_ant > close_ant and open_atual > close_atual and close_atual < open_ant:
#         #msg_panico = f"Mudou para baixo {symbol} De: {open_ant} para: {close_atual}"
#         msg_panico = f"para baixo"

#     # Condição de REVERSÃO PARA CIMA (bullish)
#     elif open_ant > close_ant and low_ant < open_ant and open_atual < close_atual and close_atual > open_ant:
#         msg_panico = f"para cima"

#     # Retorna os dois closes (anterior e atual) e a mensagem (None se nenhuma condição for atendida)
#     return close_ant, close_atual, rompeu,msg_panico
#     #return msg_panico


def velocidade_preco_df(ativo, unidade='hora'):
    """
    Calcula a velocidade de variação do preço (close) com sinal.
    Retorna:
      - positivo se o preço subiu (alta)
      - negativo se o preço caiu (queda)
    """
    
    #def calcular_velocidade_media(symbol, timeframe=mt5.TIMEFRAME_M2, n_candles=5):
    
    rates = mt5.copy_rates_from_pos( ativo , mt5.TIMEFRAME_M2 , 0, 5)
    if rates is None or len(rates) < 2:
        return None
    df = pd.DataFrame(rates)
    
    preco_inicial = df.iloc[0]['close']
    preco_final   = df.iloc[-1]['close']
    delta_preco   = preco_final - preco_inicial   # mantém o sinal

    n_candles = len(df)
    intervalos = n_candles - 1
    intervalo_minutos = 2   # TIMEFRAME_M2
    delta_tempo_horas = intervalos * (intervalo_minutos / 60.0)

    if delta_tempo_horas == 0:
        return 0.0

    velocidade = delta_preco / delta_tempo_horas   # sinal preservado

    # Conversão opcional para outra unidade (ex: minuto, segundo)
    if unidade == 'minuto':
        velocidade = velocidade / 60.0
    elif unidade == 'segundo':
        velocidade = velocidade / 3600.0

    return velocidade



import pandas as pd

def calcular_velocidade_aceleracao(df, intervalo_minutos=2):
    """
    Calcula velocidade (R$/hora) e aceleração (R$/hora²) a partir de candles.
    
    Parâmetros:
        df: DataFrame com coluna 'close' (mínimo 2 para velocidade, 3 para aceleração)
        intervalo_minutos: duração de cada candle em minutos (padrão 2)
    
    Retorna:
        (velocidade_atual, aceleracao) onde:
            velocidade_atual: taxa de variação no último intervalo (positiva=alta, negativa=queda)
            aceleracao: variação da velocidade entre os dois últimos intervalos
                        (positiva = movimento está acelerando para cima ou freando queda)
    """
    if len(df) < 2:
        return 0.0, 0.0
    
    intervalo_horas = intervalo_minutos / 60.0
    
    # Velocidade em cada intervalo consecutivo
    velocidades = []
    for i in range(1, len(df)):
        delta_preco = df.iloc[i]['close'] - df.iloc[i-1]['close']
        velocidades.append(delta_preco / intervalo_horas)
    
    vel_atual = velocidades[-1]
    
    # Aceleração: diferença entre últimas duas velocidades dividida pelo tempo
    if len(velocidades) >= 2:
        delta_vel = velocidades[-1] - velocidades[-2]
        # O tempo entre os pontos médios dos intervalos é igual ao intervalo do candle
        aceleracao = delta_vel / intervalo_horas
    else:
        aceleracao = 0.0
    
    return vel_atual, aceleracao


def rompimento_saida(opcao, n=1, timeframe=5):  # timeframe é um número (1 a 30, apenas alguns suportados)
    symbol = ativo_principal(opcao)
    
    # Mapeamento de minutos para constantes TIMEFRAME do MT5
    tf_map = {
        1: mt5.TIMEFRAME_M1,
        2: mt5.TIMEFRAME_M2,
        3: mt5.TIMEFRAME_M3,
        4: mt5.TIMEFRAME_M4,
        5: mt5.TIMEFRAME_M5,
        6: mt5.TIMEFRAME_M6,
        10: mt5.TIMEFRAME_M10,
        12: mt5.TIMEFRAME_M12,
        15: mt5.TIMEFRAME_M15,
        20: mt5.TIMEFRAME_M20,
        30: mt5.TIMEFRAME_M30,
    }
    
    # Verifica se o timeframe solicitado é suportado
    if timeframe not in tf_map:
        print(f"Timeframe {timeframe} minutos não suportado. Use um dos: {list(tf_map.keys())}")
        return None
    
    tf_const = tf_map[timeframe]
    
    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 5)
    msg_panico = "-"
    if rates is None or len(rates) < 5:
        return msg_panico

    df = pd.DataFrame(rates)
    close_atual = df.iloc[-1]['close']
    open_atual  = df.iloc[-1]['open']
    high_atual  = df.iloc[-1]['high']
    low_atual   = df.iloc[-1]['low']


    close_ant = df.iloc[-2]['close']
    open_ant  = df.iloc[-2]['open']
    high_ant  = df.iloc[-2]['high']
    low_ant   = df.iloc[-2]['low']

    velas_base = df.iloc[-n-1:-1]
    max_base = max(velas_base['high'].max(), velas_base['close'].max())
    min_base = min(velas_base['low'].min(), velas_base['close'].min())
    ultimo_close = df.iloc[-1]['close']
    rompeu = ultimo_close > max_base or ultimo_close < min_base
    positivo= "^" if ultimo_close > max_base  else ("v" if ultimo_close < min_base else "-")
    
    ab="00" 
    rates = mt5.copy_rates_from_pos(opcao, tf_const, 0, 5) 
    if rates is not None or len(rates) > 3:
        df = pd.DataFrame(rates)
        velocidade, aceleracao = calcular_velocidade_aceleracao(df, intervalo_minutos=2)
        LIMIAR_ACELERACAO = 10  # R$/hora², ajuste conforme necessário
        if abs(aceleracao) > LIMIAR_ACELERACAO:
            ab=(f"AcBr: {aceleracao:.2f} R$/h²")
            # aqui você pode acionar seu alarme ou lógica de pânico





    sentido = "^" if high_atual - close_atual < close_atual - low_atual else ("v" if high_atual - close_atual > close_atual - low_atual else "=")


    if open_ant < close_ant and high_ant > close_ant and open_atual > close_atual and close_atual < open_ant:
        msg_panico = "v"#"para baixo"
    elif open_ant > close_ant and low_ant < open_ant and open_atual < close_atual and close_atual > open_ant:
        msg_panico = "^" #"para cima"

        
    
    
    
    
    
    return rompeu, positivo,msg_panico, sentido, ab


def detectar_lateralizacao(df, n=5, tolerancia=0.002):
    """
    df: DataFrame com colunas ['time','open','high','low','close']
    n: número de velas para considerar na lateralização
    tolerancia: percentual máximo de variação permitido (ex: 0.002 = 0.2%)
    """

    # pega as últimas n velas
    ultimas = df.tail(n)

    # calcula faixa de preços (considerando open e close)
    valores = list(ultimas['open']) + list(ultimas['close'])
    max_val = max(valores)
    min_val = min(valores)

    # verifica se range está dentro da tolerância
    faixa = (max_val - min_val) / max_val
    lateralizado = faixa <= tolerancia

    # última vela
    ultima = df.iloc[-1]
    rompeu = ultima['close'] > max_val or ultima['close'] < min_val

    return {
        "lateralizado": lateralizado,
        "faixa_min": min_val,
        "faixa_max": max_val,
        "ultima_rompeu": rompeu,
        "ultima_close": ultima['close']
    }


def detectar_quebra_lateralizacao(df, n=3, tolerancia=0.002):
    """
    df: DataFrame com colunas ['open','close']
    n: número de velas para considerar como 'faixa lateral'
    tolerancia: percentual máximo de variação permitido
    """

    # pega as últimas n velas antes da última
    base = df.iloc[-(n+1):-1]

    # calcula faixa de preços (open/close)
    valores = list(base['open']) + list(base['close'])
    max_val = max(valores)
    min_val = min(valores)

    faixa = (max_val - min_val) / max_val
    lateralizado = faixa <= tolerancia

    # última vela
    ultima = df.iloc[-1]
    rompeu = ultima['close'] > max_val or ultima['close'] < min_val

    return {
        "lateralizado": lateralizado,
        "faixa_min": min_val,
        "faixa_max": max_val,
        "ultima_close": ultima['close'],
        "ultima_rompeu": rompeu
    }




#novo em teste
def determinar_direcao_RSI_kamikazi(opcao):
    limiar_aprox=1.5 
    peso_reversao=1.0
    
    """
    Versão autossuficiente: não depende de MT5, ativo_principal etc.
    Parâmetros:
        close_prices  : array-like (lista, numpy array ou pandas Series) com preços de fechamento.
        limiar_aprox  : float, sensibilidade para detectar reversão antecipada (padrão 1.5)
        peso_reversao : float, peso adicional para reversão antecipada (padrão 1.0)
    Retorna:
        direcao, impulso, cruzamentos, tendencia_diff, recomendacao
    """
    # Converte para pandas Series se necessário
     # Obtém o símbolo
    symbol = ativo_principal(opcao)  # função externa que retorna o ticker
    symbol = "VALE3"  # fallback fixo, pode remover se a função acima funcionar
    timeframe = mt5.TIMEFRAME_M30
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
    if rates is None or len(rates) < 50:
        return "erro", "dados_insuficientes", [], "indefinida", "AGUARDAR (dados insuficientes)"
    
    df = pd.DataFrame(rates)
    close_prices = df['close']
    
    
    
    
    
    
    # Dados da última vela (baseado apenas no fechamento, sem open)
    # ----- Dados da última vela -----
    ultimo_close = df['close'].iloc[-1]
    ultimo_open = df['open'].iloc[-1]
    if ultimo_close > ultimo_open:
        tipo_vela = "positiva"
    elif ultimo_close < ultimo_open:
        tipo_vela = "negativa"
    else:
        tipo_vela = "neutra"
    
    
    
        
    # Calcula RSI(5) e EMA(9) sobre o RSI
    rsi_5 = calculate_rsi(close_prices, period=5)
    ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
    # Remove NaNs iniciais
    rsi_5 = rsi_5.dropna()
    ema_9_rsi = ema_9_rsi.dropna()
    
    # Últimos 5 valores
    rsi_list = rsi_5.tail(5).tolist()
    ma_list = ema_9_rsi.tail(5).tolist()
    
    if len(rsi_list) < 5:
        return "dados_insuficientes", "poucos_dados", [], "indefinida", "AGUARDAR (poucos dados)"
    
    # ----- 1. Cruzamentos -----
    cruzamentos = []
    for i in range(len(rsi_list)-1):
        if rsi_list[i] < ma_list[i] and rsi_list[i+1] > ma_list[i+1]:
            cruzamentos.append(f"Alta entre {i} e {i+1}")
        elif rsi_list[i] > ma_list[i] and rsi_list[i+1] < ma_list[i+1]:
            cruzamentos.append(f"Baixa entre {i} e {i+1}")
    
    # ----- 2. Diferenças e tendência da diferença -----
    diff_list = [rsi_list[j] - ma_list[j] for j in range(5)]
    variacoes = [diff_list[i+1] - diff_list[i] for i in range(4)]
    
    if all(v == 0 for v in variacoes):
        tendencia_diff = "estável"
    elif all(v > 0 for v in variacoes):
        tendencia_diff = "crescente"
    elif all(v < 0 for v in variacoes):
        tendencia_diff = "decrescente"
    else:
        tendencia_diff = "flutuante"
    
    # ----- 3. Classificação do impulso -----
    diff_atual = diff_list[-1]
    if diff_atual > 0:
        posicao = "acima_da_MA"
    elif diff_atual < 0:
        posicao = "abaixo_da_MA"
    else:
        posicao = "neutro"
    
    if tendencia_diff == "crescente":
        if diff_atual < 0:
            impulso = "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"
        else:
            impulso = "ACELERAÇÃO DE ALTA (RSI se afastando para cima)"
    elif tendencia_diff == "decrescente":
        if diff_atual > 0:
            impulso = "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"
        else:
            impulso = "ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)"
    elif tendencia_diff == "estável":
        impulso = "IMPULSO NEUTRO (diferença constante)"
    else:
        impulso = "IMPULSO INDEFINIDO (oscilação sem direção clara)"
    
    # ----- 4. Direção final (com reversão antecipada) -----
    rsi_atual = rsi_list[-1]
    ma_atual = ma_list[-1]
    
    if rsi_atual < ma_atual and tendencia_diff == "crescente":
        if diff_atual > -limiar_aprox:
            direcao = "vai subir (reversão antecipada)"
        else:
            direcao = "vai descer (aproximação por baixo)"
    elif rsi_atual > ma_atual and tendencia_diff == "decrescente":
        if diff_atual < limiar_aprox:
            direcao = "vai descer (reversão antecipada)"
        else:
            direcao = "vai subir (aproximação por cima)"
    else:
        if rsi_atual > ma_atual:
            direcao = "vai subir"
        elif rsi_atual < ma_atual:
            direcao = "vai descer"
        else:
            direcao = "parado"
    
    # ----- 5. Força e recomendação (com peso_reversao ajustável) -----
    forca_alta = 0
    forca_baixa = 0
    
    if (direcao == "vai subir") or (direcao == "vai subir (reversão antecipada)"):
        if impulso in ["ACELERAÇÃO DE ALTA (RSI se afastando para cima)", 
                       "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"]:
            forca_alta += 2
        if "Alta" in str(cruzamentos):
            forca_alta += 2
        if tendencia_diff == "crescente":
            forca_alta += 1
        if diff_atual > 5:
            forca_alta += 1
        # Bônus ajustável para reversão antecipada
        if direcao == "vai subir (reversão antecipada)":
            forca_alta += peso_reversao
    
    if (direcao == "vai descer") or (direcao == "vai descer (reversão antecipada)"):
        if impulso in ["ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)", 
                       "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"]:
            forca_baixa += 2
        if "Baixa" in str(cruzamentos):
            forca_baixa += 2
        if tendencia_diff == "decrescente":
            forca_baixa += 1
        if diff_atual < -5:
            forca_baixa += 1
        if direcao == "vai descer (reversão antecipada)":
            forca_baixa += peso_reversao
    
    # Decisão da recomendação
    if forca_alta >= 3:
        recomendacao = "COMPRA DE CALL"
    elif forca_alta >= 2:
        if "reversão antecipada" in direcao:
            recomendacao = "COMPRA DE CALL (antecipada)"
        else:
            recomendacao = "COMPRA DE CALL (moderada)"
    elif forca_baixa >= 3:
        recomendacao = "COMPRA DE PUT"
    elif forca_baixa >= 2:
        if "reversão antecipada" in direcao:
            recomendacao = "COMPRA DE PUT (antecipada)"
        else:
            recomendacao = "COMPRA DE PUT (moderada)"
    elif forca_baixa >= 1 and ("vai descer" in direcao):
        recomendacao = "VENDA DE CALL (estratégia conservadora)"
    elif forca_alta >= 1 and ("vai subir" in direcao):
        recomendacao = "VENDA DE PUT (estratégia conservadora)"
    else:
        recomendacao = "AGUARDAR"
    
    # Se ainda não definiu mas há cruzamento
    if recomendacao == "AGUARDAR" and cruzamentos:
        if "Alta" in str(cruzamentos[-1]):
            recomendacao = "COMPRA DE CALL (cruzamento recente)"
        elif "Baixa" in str(cruzamentos[-1]):
            recomendacao = "COMPRA DE PUT (cruzamento recente)"
    
    # ----- Verificação de conflito com a última vela -----
    if tipo_vela == "positiva" and ("VENDA DE CALL" in recomendacao or "COMPRA DE PUT" in recomendacao):
        recomendacao = "AGUARDAR (vela positiva conflita com sinal de baixa)"
    elif tipo_vela == "negativa" and ("COMPRA DE CALL" in recomendacao or "VENDA DE PUT" in recomendacao):
        recomendacao = "AGUARDAR (vela negativa conflita com sinal de alta)"
    
    # Impressão para depuração (opcional)
    if cruzamentos:
        print(f"Cruzamentos: {cruzamentos}")
    else:
        print("Nenhum cruzamento.")
    print(f"Direção: {direcao}")
    print(f"RecomendaçãoKami: {recomendacao}")
    
    return direcao, impulso, cruzamentos, tendencia_diff, recomendacao


#original testar a versao novo
# def determinar_direcao_RSI_kamikazi(opcao):
#     """
#     Analisa RSI(5) e sua EMA(9) para determinar direção, impulso, cruzamentos
#     e recomendar operações com opções (call/put).
    
#     Parâmetros:
#         opcao: parâmetro para obter o símbolo via ativo_principal(opcao)
    
#     Retorna:
#         direcao (str): "vai subir", "vai descer" ou "parado"
#         impulso (str): descrição do impulso
#         cruzamentos (list): lista de strings com cruzamentos detectados
#         tendencia_diff (str): "crescente", "decrescente", "estável" ou "flutuante"
#         recomendacao (str): recomendação final
#     """
#     # Obtém o símbolo
#     symbol = ativo_principal(opcao)  # função externa que retorna o ticker
#     symbol = "VALE3"  # fallback fixo, pode remover se a função acima funcionar
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
#     if rates is None or len(rates) < 50:
#         return "erro", "dados_insuficientes", [], "indefinida", "AGUARDAR (dados insuficientes)"
    
#     df = pd.DataFrame(rates)
#     close_prices = df['close']
    
#     # ----- Dados da última vela -----
#     ultimo_close = df['close'].iloc[-1]
#     ultimo_open = df['open'].iloc[-1]
#     if ultimo_close > ultimo_open:
#         tipo_vela = "positiva"
#     elif ultimo_close < ultimo_open:
#         tipo_vela = "negativa"
#     else:
#         tipo_vela = "neutra"


#     # Calcula RSI(5) (método Wilder) e EMA(9) sobre o RSI
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
#     # Remove NaNs iniciais
#     rsi_5 = rsi_5.dropna()
#     ema_9_rsi = ema_9_rsi.dropna()
    
#     # Obtém os últimos 5 valores
#     rsi_list = rsi_5.tail(5).tolist()
#     ma_list = ema_9_rsi.tail(5).tolist()
    
#     if len(rsi_list) < 5:
#         return "dados_insuficientes", "poucos_dados", [], "indefinida", "AGUARDAR (poucos dados)"
    
#     # ----- 1. Cruzamentos -----
#     cruzamentos = []
#     for i in range(len(rsi_list)-1):
#         if rsi_list[i] < ma_list[i] and rsi_list[i+1] > ma_list[i+1]:
#             cruzamentos.append(f"Alta entre {i} e {i+1}")
#         elif rsi_list[i] > ma_list[i] and rsi_list[i+1] < ma_list[i+1]:
#             cruzamentos.append(f"Baixa entre {i} e {i+1}")
    
#     # ----- 2. Diferenças e tendência da diferença -----
#     diff_list = [rsi_list[j] - ma_list[j] for j in range(5)]
#     variacoes = [diff_list[i+1] - diff_list[i] for i in range(4)]
    
#     if all(v == 0 for v in variacoes):
#         tendencia_diff = "estável"
#     elif all(v > 0 for v in variacoes):
#         tendencia_diff = "crescente"
#     elif all(v < 0 for v in variacoes):
#         tendencia_diff = "decrescente"
#     else:
#         tendencia_diff = "flutuante"
    
#     # ----- 3. Classificação do impulso -----
#     diff_atual = diff_list[-1]
#     if diff_atual > 0:
#         posicao = "acima_da_MA"
#     elif diff_atual < 0:
#         posicao = "abaixo_da_MA"
#     else:
#         posicao = "neutro"
    
#     if tendencia_diff == "crescente":
#         if diff_atual < 0:
#             impulso = "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"
#         else:
#             impulso = "ACELERAÇÃO DE ALTA (RSI se afastando para cima)"
#     elif tendencia_diff == "decrescente":
#         if diff_atual > 0:
#             impulso = "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"
#         else:
#             impulso = "ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)"
#     elif tendencia_diff == "estável":
#         impulso = "IMPULSO NEUTRO (diferença constante)"
#     else:
#         impulso = "IMPULSO INDEFINIDO (oscilação sem direção clara)"
    
#     # ----- 4. Direção final -----
#     rsi_atual = rsi_list[-1]
#     ma_atual = ma_list[-1]
    
#     if rsi_atual > ma_atual:
#         direcao = "vai subir"
#     elif rsi_atual < ma_atual:
#         direcao = "vai descer"
#     else:
#         direcao = "parado"
    
#     # ----- 5. Recomendação de operações (Call / Put) -----
#     # Força da tendência de alta (para compra de call)
    
    
#     forca_alta = 0
    
    
    
#     if direcao == "vai subir":
#         if impulso in ["ACELERAÇÃO DE ALTA (RSI se afastando para cima)", 
#                        "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"]:
#             forca_alta += 2
#         if "Alta" in str(cruzamentos):
#             forca_alta += 2
#         if tendencia_diff == "crescente":
#             forca_alta += 1
#         if diff_atual > 5:
#             forca_alta += 1
    
#     # Força da tendência de baixa (para compra de put)
#     forca_baixa = 0
#     if direcao == "vai descer":
#         if impulso in ["ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)", 
#                        "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"]:
#             forca_baixa += 2
#         if "Baixa" in str(cruzamentos):
#             forca_baixa += 2
#         if tendencia_diff == "decrescente":
#             forca_baixa += 1
#         if diff_atual < -5:
#             forca_baixa += 1
    
#     # Decisão da recomendação
#     if forca_alta >= 3:
#         recomendacao = "COMPRA DE CALL"
#     elif forca_alta >= 2:
#         recomendacao = "COMPRA DE CALL (moderada)"
#     elif forca_baixa >= 3:
#         recomendacao = "COMPRA DE PUT"
#     elif forca_baixa >= 2:
#         recomendacao = "COMPRA DE PUT (moderada)"
#     elif forca_baixa >= 1 and direcao == "vai descer":
#         recomendacao = "VENDA DE CALL (estratégia conservadora)"
#     elif forca_alta >= 1 and direcao == "vai subir":
#         recomendacao = "VENDA DE PUT (estratégia conservadora)"
#     else:
#         recomendacao = "AGUARDAR"
    
#     # Se ainda não definiu mas há cruzamento, dá uma sugestão baseada no último cruzamento
#     if recomendacao == "AGUARDAR" and cruzamentos:
#         if "Alta" in str(cruzamentos[-1]):
#             recomendacao = "COMPRA DE CALL (cruzamento recente)"
#         elif "Baixa" in str(cruzamentos[-1]):
#             recomendacao = "COMPRA DE PUT (cruzamento recente)"
    
#     # ----- 6. Verificação de conflito com a última vela -----
#     # Impede recomendação de baixa em vela positiva
#     if tipo_vela == "positiva" and ("VENDA DE CALL" in recomendacao or "COMPRA DE PUT" in recomendacao):
#         recomendacao = "AGUARDAR (vela positiva conflita com sinal de baixa)"
#     # Impede recomendação de alta em vela negativa
#     elif tipo_vela == "negativa" and ("COMPRA DE CALL" in recomendacao or "VENDA DE PUT" in recomendacao):
#         recomendacao = "AGUARDAR (vela negativa conflita com sinal de alta)"
#     # ----- 6. Verificação com base no tipo detalhado da vela -----



#     # ----- 6. Exibição (opcional) -----
#     # print(f"RSI: {[round(x,2) for x in rsi_list]}")
#     # print(f"MA : {[round(x,2) for x in ma_list]}")
#     # print(f"Diferenças: {[round(d,2) for d in diff_list]}")
#     # print(f"Tendência da diferença: {tendencia_diff}")
#     # print(f"Impulso: {impulso}")
#     if cruzamentos:
#         print(f"Cruzamentos: {cruzamentos}")
#     else:
#         print("Nenhum cruzamento.")
#     print(f"Direção: {direcao}")
#     print(f"RecomendaçãoKami: {recomendacao}")
    
#     return direcao, impulso, cruzamentos, tendencia_diff, recomendacao

# def determinar_direcao_RSI(opcao):
#     """
#     Analisa RSI(5) e sua EMA(9) para determinar direção, impulso, cruzamentos
#     e recomendar operações com opções (call/put).
    
#     Parâmetros:
#         opcao: parâmetro para obter o símbolo via ativo_principal(opcao)
    
#     Retorna:
#         direcao (str): "vai subir", "vai descer" ou "parado"
#         impulso (str): descrição do impulso
#         cruzamentos (list): lista de strings com cruzamentos detectados
#         tendencia_diff (str): "crescente", "decrescente", "estável" ou "flutuante"
#         recomendacao (str): recomendação final
#     """
#     # Obtém o símbolo
#     symbol = ativo_principal(opcao)  # função externa que retorna o ticker
#     symbol = "VALE3"  # fallback fixo, pode remover se a função acima funcionar
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
#     if rates is None or len(rates) < 50:
#         return "erro", "dados_insuficientes", [], "indefinida", "AGUARDAR (dados insuficientes)"
    
#     df = pd.DataFrame(rates)
#     close_prices = df['close']
    
#     # Calcula RSI(5) (método Wilder) e EMA(9) sobre o RSI
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
#     # Remove NaNs iniciais
#     rsi_5 = rsi_5.dropna()
#     ema_9_rsi = ema_9_rsi.dropna()
    
#     # Obtém os últimos 5 valores
#     rsi_list = rsi_5.tail(5).tolist()
#     ma_list = ema_9_rsi.tail(5).tolist()
    
#     if len(rsi_list) < 5:
#         return "dados_insuficientes", "poucos_dados", [], "indefinida", "AGUARDAR (poucos dados)"
    
#     # ----- 1. Cruzamentos -----
#     cruzamentos = []
#     for i in range(len(rsi_list)-1):
#         if rsi_list[i] < ma_list[i] and rsi_list[i+1] > ma_list[i+1]:
#             cruzamentos.append(f"Alta entre {i} e {i+1}")
#         elif rsi_list[i] > ma_list[i] and rsi_list[i+1] < ma_list[i+1]:
#             cruzamentos.append(f"Baixa entre {i} e {i+1}")
    
#     # ----- 2. Diferenças e tendência da diferença -----
#     diff_list = [rsi_list[j] - ma_list[j] for j in range(5)]
#     variacoes = [diff_list[i+1] - diff_list[i] for i in range(4)]
    
#     if all(v == 0 for v in variacoes):
#         tendencia_diff = "estável"
#     elif all(v > 0 for v in variacoes):
#         tendencia_diff = "crescente"
#     elif all(v < 0 for v in variacoes):
#         tendencia_diff = "decrescente"
#     else:
#         tendencia_diff = "flutuante"
    
#     # ----- 3. Classificação do impulso -----
#     diff_atual = diff_list[-1]
#     if diff_atual > 0:
#         posicao = "acima_da_MA"
#     elif diff_atual < 0:
#         posicao = "abaixo_da_MA"
#     else:
#         posicao = "neutro"
    
#     if tendencia_diff == "crescente":
#         if diff_atual < 0:
#             impulso = "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"
#         else:
#             impulso = "ACELERAÇÃO DE ALTA (RSI se afastando para cima)"
#     elif tendencia_diff == "decrescente":
#         if diff_atual > 0:
#             impulso = "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"
#         else:
#             impulso = "ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)"
#     elif tendencia_diff == "estável":
#         impulso = "IMPULSO NEUTRO (diferença constante)"
#     else:
#         impulso = "IMPULSO INDEFINIDO (oscilação sem direção clara)"
    
#     # ----- 4. Direção final -----
#     rsi_atual = rsi_list[-1]
#     ma_atual = ma_list[-1]
    
#     if rsi_atual > ma_atual:
#         direcao = "vai subir"
#     elif rsi_atual < ma_atual:
#         direcao = "vai descer"
#     else:
#         direcao = "parado"
    
#     # ----- 5. Recomendação de operações (Call / Put) com trava de segurança -----
#     recomendacao = "AGUARDAR"
    
#     # 🔒 SEGURANÇA: se impulso for indefinido, não opera
#     if impulso == "IMPULSO INDEFINIDO (oscilação sem direção clara)":
#         recomendacao = "AGUARDAR (impulso indefinido, risco elevado)"
#     else:
#         # Força da tendência de alta (para compra de call)
#         forca_alta = 0
#         if direcao == "vai subir":
#             if impulso in ["ACELERAÇÃO DE ALTA (RSI se afastando para cima)", 
#                            "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"]:
#                 forca_alta += 2
#             if "Alta" in str(cruzamentos):
#                 forca_alta += 2
#             if tendencia_diff == "crescente":
#                 forca_alta += 1
#             if diff_atual > 5:
#                 forca_alta += 1
        
#         # Força da tendência de baixa (para compra de put)
#         forca_baixa = 0
#         if direcao == "vai descer":
#             if impulso in ["ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)", 
#                            "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"]:
#                 forca_baixa += 2
#             if "Baixa" in str(cruzamentos):
#                 forca_baixa += 2
#             if tendencia_diff == "decrescente":
#                 forca_baixa += 1
#             if diff_atual < -5:
#                 forca_baixa += 1
        
#         # Decisão da recomendação
#         if forca_alta >= 3:
#             recomendacao = "COMPRA DE CALL"
#         elif forca_alta >= 2:
#             recomendacao = "COMPRA DE CALL (moderada)"
#         elif forca_baixa >= 3:
#             recomendacao = "COMPRA DE PUT"
#         elif forca_baixa >= 2:
#             recomendacao = "COMPRA DE PUT (moderada)"
#         elif forca_baixa >= 1 and direcao == "vai descer":
#             recomendacao = "VENDA DE CALL (estratégia conservadora)"
#         elif forca_alta >= 1 and direcao == "vai subir":
#             recomendacao = "VENDA DE PUT (estratégia conservadora)"
#         else:
#             recomendacao = "AGUARDAR"
        
#         # Se ainda não definiu mas há cruzamento, dá uma sugestão (opcional)
#         if recomendacao == "AGUARDAR" and cruzamentos:
#             if "Alta" in str(cruzamentos[-1]):
#                 recomendacao = "COMPRA DE CALL (cruzamento recente)"
#             elif "Baixa" in str(cruzamentos[-1]):
#                 recomendacao = "COMPRA DE PUT (cruzamento recente)"
    
#     # ----- 6. Exibição (opcional) -----
#     print(f"RSI: {[round(x,2) for x in rsi_list]}")
#     print(f"MA : {[round(x,2) for x in ma_list]}")
#     print(f"Diferenças: {[round(d,2) for d in diff_list]}")
#     print(f"Tendência da diferença: {tendencia_diff}")
#     print(f"Impulso: {impulso}")
#     if cruzamentos:
#         print(f"Cruzamentos: {cruzamentos}")
#     else:
#         print("Nenhum cruzamento.")
#     print(f"Direção: {direcao}")
#     print(f"Recomendação: {recomendacao}")
    
#     return direcao, impulso, cruzamentos, tendencia_diff, recomendacao

def vela_volume(df, posicao):
    """
    Analisa a vela na posição especificada e retorna código de cor/volume.

    Parâmetros:
        df: DataFrame com colunas 'open', 'high', 'low', 'close'.
            Deve estar ordenado do mais antigo (índice 0) para o mais recente (índice -1).
        posicao: 0 = vela mais recente (última linha), 1 = anterior, etc.

    Retorna:
        str: "G" (verde, volume > anterior), "g" (verde, volume < anterior),
             "R" (vermelho, volume > anterior), "r" (vermelho, volume < anterior),
             "+" (neutro ou volume igual ao anterior).
    """
    # Índice da vela no DataFrame
    idx = len(df) - 1 - posicao
    if idx < 0 or idx >= len(df):
        return "?"  # posição inválida

    open_ = df.iloc[idx]['open']
    close_ = df.iloc[idx]['close']

    # Volume da vela atual (tamanho do corpo)
    volume = abs(open_ - close_)

    # Volume da vela anterior (posicao + 1)
    idx_prev = len(df) - 1 - (posicao + 1)
    if idx_prev >= 0:
        open_prev = df.iloc[idx_prev]['open']
        close_prev = df.iloc[idx_prev]['close']
        volume_prev = abs(open_prev - close_prev)
    else:
        volume_prev = 0  # se não existir vela anterior

    # Classificação
    if open_ < close_:          # vela de alta (verde)
        return "G" if volume > volume_prev else "g"
    elif open_ > close_:        # vela de baixa (vermelha)
        return "R" if volume > volume_prev else "r"
    else:                       # vela neutra (doji)
        return "+"

# def verificar_reversao(antigo, novo):
#     """Retorna descrição se houve reversão positiva<->negativa, senão None."""
#     positivo = {'G', 'g'}
#     negativo = {'R', 'r'}
#     if antigo in positivo and novo in negativo:
#         return "positiva -> negativa"
#     elif antigo in negativo and novo in positivo:
#         return "negativa -> positiva"
#     return None

# def verificar_reversao(antigo, novo):
#     """Retorna descrição se houve reversão positiva<->negativa, senão None."""
#     positivo = {'G', 'g'}
#     negativo = {'R', 'r'}
    
#     # Classifica como negativo se um G (maiúsculo ou minúsculo) se torna g ou r
#     if antigo in {'G'} and novo in {'g', 'r'}:
#         return "negativa"
#     # Classifica como positivo se um R (maiúsculo ou minúsculo) se torna r ou g
#     elif antigo in {'R'} and novo in {'r', 'g'}:
#         return "positiva"
    
#     # Mantém a lógica original para reversões entre classes
#     if antigo in positivo and novo in negativo:
#         return "negativa"#"positiva -> negativa"
#     elif antigo in negativo and novo in positivo:
#         return "positiva"#"negativa -> positiva"
    
#     return None

# def verificar_reversao(antigo, novo):
#     """Retorna 'negativa' ou 'positiva' se houve reversão, senão None."""
#     positivo = {'G', 'g'}
#     negativo = {'R', 'r'}
    

#     # Negativa: perda de força ou desvalorização
#     if antigo == 'G' and novo in {'g', 'r'}:  # G forte -> g fraco ou r negativo
#         return "negativa"
#     elif antigo == 'g' and novo == 'r':       # g fraco -> r negativo
#         return "negativa"
#     elif antigo == 'g' and novo == '+':       # g fraco -> r negativo
#         return "negativa"
    
#     elif antigo == 'r' and novo == 'R':       # r fraco -> R forte (desvalorizando)
#         return "negativa"
#     elif antigo in positivo and novo in negativo:  # G/g -> R/r
#         return "negativa"
    



#     # Positiva: ganho de força ou valorização
#     elif antigo == 'g' and novo == 'G':       # g fraco -> G forte (valorizando)
#         return "positiva"
#     elif antigo == 'R' and novo in {'r', 'g'}: # R forte -> r fraco ou g positivo
#         return "positiva"
#     elif antigo == 'r' and novo == 'g':       # r fraco -> g positivo
#         return "positiva"
#     elif antigo == 'r' and novo == '+':       # r fraco -> g positivo
#         return "positiva"
    
    
#     elif antigo in negativo and novo in positivo:  # R/r -> G/g
#         return "positiva"
    
#     return None

def verificar_reversao(antigo, novo): #felipe
    """Retorna 'negativa' ou 'positiva' se houve reversão, senão baseado no valor."""
    positivo = {'G', 'g'}
    negativo = {'R', 'r'}
    
    # Se não houve mudança, baseado no valor
    if antigo == novo:
        if antigo in positivo:  # 'g' ou 'G'
            return "positiva"
        else:  # 'r' ou 'R' (ou qualquer outro)
            return "negativa"
    
    # Negativa: perda de força ou desvalorização
    if antigo == 'G' and novo in {'g', 'r'}:  # G forte -> g fraco ou r negativo
        return "negativa1"
    elif antigo == 'g' and novo == 'r':       # g fraco -> r negativo
        return "negativa2"
    elif antigo == 'g' and novo == '+':       # g fraco -> r negativo
        return "negativa3"
    elif antigo == 'r' and novo == 'R':       # r fraco -> R forte (desvalorizando)
        return "negativa4"
    elif antigo in positivo and novo in negativo:  # G/g -> R/r
        return "negativa5"
    
    # Positiva: ganho de força ou valorização
    elif antigo == 'g' and novo == 'G':       # g fraco -> G forte (valorizando)
        return "positiva1"
    elif antigo == 'R' and novo in {'r', 'g'}: # R forte -> r fraco ou g positivo
        return "positiva2"
    elif antigo == 'r' and novo == 'g':       # r fraco -> g positivo
        return "positiva3"
    elif antigo == 'r' and novo == '+':       # r fraco -> g positivo
        return "positiva4"
    elif antigo in negativo and novo in positivo:  # R/r -> G/g
        return "positiva5"
    
    return "negativa."  # Qualquer outro caso retorna negativa




def sinal_opcoes_30min(opcao ):#,  rsi_list, ma_list):
    """
    Versão otimizada para opções 30min
    Usa 5 velas (2.5 horas) - equilíbrio perfeito entre velocidade e confiabilidade
    """
    symbol = ativo_principal(opcao)
    timeframe = mt5.TIMEFRAME_M30
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    if rates is None or len(rates) < 50:
        return "erro", "dados_insuficientes", [], "indefinida", "AGUARDAR (dados insuficientes)"

    df = pd.DataFrame(rates)
    close_prices = df['close']

    # Calcula RSI(5) e EMA(9) sobre o RSI
    rsi_5 = calculate_rsi(close_prices, period=5)
    ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()

    rsi_5 = rsi_5.dropna()
    ema_9_rsi = ema_9_rsi.dropna()

    rsi_list = rsi_5.tail(14).tolist()
    ma_list = ema_9_rsi.tail(14).tolist()
    
    if len(rsi_list) < 5:
        return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
    # Converter para numpy
    rsi = np.array(rsi_list[-5:])
    ma = np.array(ma_list[-5:])
    diff = rsi - ma
    
    # 1. Tendência linear (inclinação)
    x = np.arange(5)
    slope = np.polyfit(x, diff, 1)[0]
    
    # 2. Velocidade atual (última variação)
    velocidade = diff[-1] - diff[-2] if len(diff) >= 2 else 0
    
    # 3. Aceleração (mudança na velocidade)
    if len(diff) >= 3:
        aceleracao = (diff[-1] - diff[-2]) - (diff[-2] - diff[-3])
    else:
        aceleracao = 0
    
    # Sistema de pontuação (pesos)
    score = 0
    
    # Inclinação (peso 3 - mais importante)
    if slope > 0.15:
        score += 3
    elif slope > 0.05:
        score += 1.5
    elif slope < -0.15:
        score -= 3
    elif slope < -0.05:
        score -= 1.5
    
    # Velocidade (peso 2)
    if velocidade > 0.2:
        score += 2
    elif velocidade > 0.05:
        score += 1
    elif velocidade < -0.2:
        score -= 2
    elif velocidade < -0.05:
        score -= 1
    
    # Aceleração (peso 1 - confirmação)
    if aceleracao > 0.1:
        score += 1
    elif aceleracao < -0.1:
        score -= 1
    
    # Decisão com thresholds ajustados
    if score >= 3.5:
        sinal = "CALL"
        confianca = 0.85
        motivo = "tendencia_forte_alta"
    elif score >= 1.5:
        sinal = "CALL"
        confianca = 0.65
        motivo = "tendencia_moderada_alta"
    elif score <= -3.5:
        sinal = "PUT"
        confianca = 0.85
        motivo = "tendencia_forte_baixa"
    elif score <= -1.5:
        sinal = "PUT"
        confianca = 0.65
        motivo = "tendencia_moderada_baixa"
    else:
        sinal = "NEUTRO"
        confianca = 0.3
        motivo = "sem_tendencia_clara"
    
      
    # Dados para análise
    dados_mercado = {
        'rsi_list': rsi_list,
        'ma_list': ma_list,
        'preco_atual': close_prices.iloc[-1]
    }
    
    # Analisar com a rede neural
    
    #estado = rede.analisar_opcao(opcao, dados_mercado)
    estado = rede.analisar(opcao, dados_mercado)
    
    return estado['decisao']
    
    
    
    # return {
    #     'sinal': sinal,
    #     'confianca': confianca,
    #     'score': score,
    #     'motivo': motivo,
    #     'slope': slope,
    #     'velocidade': velocidade,
    #     'aceleracao': aceleracao,
    #     'diff_atual': diff[-1]
    #}
#felipe

def sinal_opcoes_30min_melhorado(opcao):
    """
    Versão otimizada para opções 30min com sistema de pesos aprimorado + IA
    """
    symbol = ativo_principal(opcao)
    timeframe = mt5.TIMEFRAME_M30
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
    if rates is None or len(rates) < 50:
        return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
    df = pd.DataFrame(rates)
    close_prices = df['close']
    
    # Calcula RSI(5) e EMA(9) sobre o RSI
    rsi_5 = calculate_rsi(close_prices, period=5)
    ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
    rsi_5 = rsi_5.dropna()
    ema_9_rsi = ema_9_rsi.dropna()
    
    rsi_list = rsi_5.tail(14).tolist()
    ma_list = ema_9_rsi.tail(14).tolist()
    
    if len(rsi_list) < 7:
        return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
    # ================== ANÁLISE COM PESOS ==================
    rsi = np.array(rsi_list[-7:])
    ma = np.array(ma_list[-7:])
    diff = rsi - ma
    
    # ✅ NORMALIZAR O DIFF
    diff_max = np.max(np.abs(diff))
    if diff_max > 0:
        diff_normalizado = diff / diff_max
    else:
        diff_normalizado = diff
    
    # Usar diff_normalizado para os cálculos
    x = np.arange(len(diff_normalizado))
    slope, intercept = np.polyfit(x, diff_normalizado, 1)
    correlacao = np.corrcoef(x, diff_normalizado)[0, 1] if len(diff_normalizado) > 1 else 0
    
    # Velocidade
    if len(diff_normalizado) >= 2:
        velocidade = diff_normalizado[-1] - diff_normalizado[-2]
        velocidade_media = np.mean(np.diff(diff_normalizado)) if len(diff_normalizado) > 2 else velocidade
    else:
        velocidade = 0
        velocidade_media = 0
    
    # Aceleração
    if len(diff_normalizado) >= 3:
        aceleracao = (diff_normalizado[-1] - diff_normalizado[-2]) - (diff_normalizado[-2] - diff_normalizado[-3])
        aceleracao_media = np.mean(np.diff(np.diff(diff_normalizado))) if len(diff_normalizado) > 3 else aceleracao
    else:
        aceleracao = 0
        aceleracao_media = 0
    
    # Momento
    if len(diff_normalizado) >= 3:
        media_ultimas_3 = np.mean(diff_normalizado[-3:])
        media_todas = np.mean(diff_normalizado)
        momento = media_ultimas_3 - media_todas
    else:
        momento = 0
    
    # Cruzamento
    cruzamento = 0
    if len(diff_normalizado) >= 2:
        if diff_normalizado[-2] < 0 and diff_normalizado[-1] > 0:
            cruzamento = 1
        elif diff_normalizado[-2] > 0 and diff_normalizado[-1] < 0:
            cruzamento = -1
    
    # ================== SISTEMA DE PONTUAÇÃO ==================
    score = 0
    detalhes_score = {}
    
    # 1. TENDÊNCIA (peso 4)
    if slope > 0.3:
        score += 4
        detalhes_score['tendencia'] = 4
    elif slope > 0.15:
        score += 3
        detalhes_score['tendencia'] = 3
    elif slope > 0.05:
        score += 1.5
        detalhes_score['tendencia'] = 1.5
    elif slope < -0.3:
        score -= 4
        detalhes_score['tendencia'] = -4
    elif slope < -0.15:
        score -= 3
        detalhes_score['tendencia'] = -3
    elif slope < -0.05:
        score -= 1.5
        detalhes_score['tendencia'] = -1.5
    else:
        detalhes_score['tendencia'] = 0
    
    # Bônus por correlação forte
    if abs(correlacao) > 0.8:
        score += 1 if slope > 0 else -1
        detalhes_score['correlacao'] = 1 if slope > 0 else -1
    else:
        detalhes_score['correlacao'] = 0
    
    # 2. VELOCIDADE (peso 3)
    if velocidade > 0.3:
        score += 3
        detalhes_score['velocidade'] = 3
    elif velocidade > 0.15:
        score += 2
        detalhes_score['velocidade'] = 2
    elif velocidade > 0.05:
        score += 1
        detalhes_score['velocidade'] = 1
    elif velocidade < -0.3:
        score -= 3
        detalhes_score['velocidade'] = -3
    elif velocidade < -0.15:
        score -= 2
        detalhes_score['velocidade'] = -2
    elif velocidade < -0.05:
        score -= 1
        detalhes_score['velocidade'] = -1
    else:
        detalhes_score['velocidade'] = 0
    
    # 3. ACELERAÇÃO (peso 2)
    if aceleracao > 0.2:
        score += 2
        detalhes_score['aceleracao'] = 2
    elif aceleracao > 0.1:
        score += 1.5
        detalhes_score['aceleracao'] = 1.5
    elif aceleracao > 0.05:
        score += 0.5
        detalhes_score['aceleracao'] = 0.5
    elif aceleracao < -0.2:
        score -= 2
        detalhes_score['aceleracao'] = -2
    elif aceleracao < -0.1:
        score -= 1.5
        detalhes_score['aceleracao'] = -1.5
    elif aceleracao < -0.05:
        score -= 0.5
        detalhes_score['aceleracao'] = -0.5
    else:
        detalhes_score['aceleracao'] = 0
    
    # 4. MOMENTO (peso 1.5)
    if momento > 0.15:
        score += 1.5
        detalhes_score['momento'] = 1.5
    elif momento > 0.05:
        score += 0.75
        detalhes_score['momento'] = 0.75
    elif momento < -0.15:
        score -= 1.5
        detalhes_score['momento'] = -1.5
    elif momento < -0.05:
        score -= 0.75
        detalhes_score['momento'] = -0.75
    else:
        detalhes_score['momento'] = 0
    
    # 5. CRUZAMENTO (peso 1)
    if cruzamento == 1:
        score += 1
        detalhes_score['cruzamento'] = 1
    elif cruzamento == -1:
        score -= 1
        detalhes_score['cruzamento'] = -1
    else:
        detalhes_score['cruzamento'] = 0
    
    # ================== DECISÃO FINAL ==================
    sinais_positivos = sum(1 for v in detalhes_score.values() if v > 0)
    sinais_negativos = sum(1 for v in detalhes_score.values() if v < 0)
    total_sinais = len([v for v in detalhes_score.values() if v != 0])
    
    if total_sinais > 0:
        consistencia = abs(sinais_positivos - sinais_negativos) / total_sinais
    else:
        consistencia = 0
    
    # Decisão com thresholds ajustados
    if score >= 6 and consistencia > 0.6:
        sinal = "CALL_FORTE"
        confianca = 0.92
        motivo = "tendencia_muito_forte_alta"
    elif score >= 4:
        sinal = "CALL"
        confianca = 0.75 + (score - 4) * 0.05
        motivo = "tendencia_forte_alta"
    elif score >= 2:
        sinal = "CALL"
        confianca = 0.60
        motivo = "tendencia_moderada_alta"
    elif score >= 0.5:
        sinal = "LEVE_CALL"
        confianca = 0.50
        motivo = "leve_tendencia_alta"
    elif score <= -6 and consistencia > 0.6:
        sinal = "PUT_FORTE"
        confianca = 0.92
        motivo = "tendencia_muito_forte_baixa"
    elif score <= -4:
        sinal = "PUT"
        confianca = 0.75 + abs(score + 4) * 0.05
        motivo = "tendencia_forte_baixa"
    elif score <= -2:
        sinal = "PUT"
        confianca = 0.60
        motivo = "tendencia_moderada_baixa"
    elif score <= -0.5:
        sinal = "LEVE_PUT"
        confianca = 0.50
        motivo = "leve_tendencia_baixa"
    else:
        sinal = "NEUTRO"
        confianca = 0.30
        motivo = "sem_tendencia_clara"
    
    confianca = min(0.98, confianca)

    # ================== DADOS PARA ANÁLISE ==================
    dados_mercado = {
        'rsi_list': rsi_list,
        'ma_list': ma_list,
        'rsi_historico': rsi_5.tail(35).tolist(),
        'ma_historico': ema_9_rsi.tail(35).tolist(),
        'preco_atual': close_prices.iloc[-1]
    }
    
    # ================== ANÁLISE COM IA ==================
    # Usar a instância 'rede' importada do cerebro
    estado = rede.analisar(opcao, dados_mercado)
    
    # ================== RETORNO ==================
    # ✅ REMOVIDA A REFERÊNCIA CIRCULAR
    return {
        'decisao': estado['decisao'],
        'sinal': sinal,
        'confianca': round(confianca, 2),
        'score': round(score, 2),
        'motivo': motivo,
        'detalhes_score': detalhes_score,
        'slope': round(slope, 4),
        'correlacao': round(correlacao, 3),
        'velocidade': round(velocidade, 4),
        'aceleracao': round(aceleracao, 4),
        'momento': round(momento, 4),
        'cruzamento': cruzamento,
        'diff_atual': round(diff[-1], 4),
        'diff_anterior': round(diff[-2], 4) if len(diff) >= 2 else None,
        'velas_analisadas': len(diff),
        'estado': estado,  # <-- Sem referência circular
    }



# def sinal_opcoes_30min_melhorado(opcao):
#     """
#     Versão otimizada para opções 30min com sistema de pesos aprimorado + IA
#     """
#     symbol = ativo_principal(opcao)
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
#     if rates is None or len(rates) < 50:
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     df = pd.DataFrame(rates)
#     close_prices = df['close']
    
#     # Calcula RSI(5) e EMA(9) sobre o RSI
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
#     rsi_5 = rsi_5.dropna()
#     ema_9_rsi = ema_9_rsi.dropna()
    
#     rsi_list = rsi_5.tail(14).tolist()
#     ma_list = ema_9_rsi.tail(14).tolist()
    
#     if len(rsi_list) < 7:
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     # ================== ANÁLISE COM PESOS ==================
#     rsi = np.array(rsi_list[-7:])
#     ma = np.array(ma_list[-7:])
#     diff = rsi - ma
    
#     # ✅ NORMALIZAR O DIFF
#     diff_max = np.max(np.abs(diff))
#     if diff_max > 0:
#         diff_normalizado = diff / diff_max
#     else:
#         diff_normalizado = diff
    
#     # Usar diff_normalizado para os cálculos
#     x = np.arange(len(diff_normalizado))
#     slope, intercept = np.polyfit(x, diff_normalizado, 1)
#     correlacao = np.corrcoef(x, diff_normalizado)[0, 1] if len(diff_normalizado) > 1 else 0
    
#     # Velocidade
#     if len(diff_normalizado) >= 2:
#         velocidade = diff_normalizado[-1] - diff_normalizado[-2]
#         velocidade_media = np.mean(np.diff(diff_normalizado)) if len(diff_normalizado) > 2 else velocidade
#     else:
#         velocidade = 0
#         velocidade_media = 0
    
#     # Aceleração
#     if len(diff_normalizado) >= 3:
#         aceleracao = (diff_normalizado[-1] - diff_normalizado[-2]) - (diff_normalizado[-2] - diff_normalizado[-3])
#         aceleracao_media = np.mean(np.diff(np.diff(diff_normalizado))) if len(diff_normalizado) > 3 else aceleracao
#     else:
#         aceleracao = 0
#         aceleracao_media = 0
    
#     # Momento
#     if len(diff_normalizado) >= 3:
#         media_ultimas_3 = np.mean(diff_normalizado[-3:])
#         media_todas = np.mean(diff_normalizado)
#         momento = media_ultimas_3 - media_todas
#     else:
#         momento = 0
    
#     # Cruzamento
#     cruzamento = 0
#     if len(diff_normalizado) >= 2:
#         if diff_normalizado[-2] < 0 and diff_normalizado[-1] > 0:
#             cruzamento = 1
#         elif diff_normalizado[-2] > 0 and diff_normalizado[-1] < 0:
#             cruzamento = -1
    
#     # ================== SISTEMA DE PONTUAÇÃO ==================
#     score = 0
#     detalhes_score = {}
    
#     # 1. TENDÊNCIA (peso 4)
#     if slope > 0.3:
#         score += 4
#         detalhes_score['tendencia'] = 4
#     elif slope > 0.15:
#         score += 3
#         detalhes_score['tendencia'] = 3
#     elif slope > 0.05:
#         score += 1.5
#         detalhes_score['tendencia'] = 1.5
#     elif slope < -0.3:
#         score -= 4
#         detalhes_score['tendencia'] = -4
#     elif slope < -0.15:
#         score -= 3
#         detalhes_score['tendencia'] = -3
#     elif slope < -0.05:
#         score -= 1.5
#         detalhes_score['tendencia'] = -1.5
#     else:
#         detalhes_score['tendencia'] = 0
    
#     # Bônus por correlação forte
#     if abs(correlacao) > 0.8:
#         score += 1 if slope > 0 else -1
#         detalhes_score['correlacao'] = 1 if slope > 0 else -1
#     else:
#         detalhes_score['correlacao'] = 0
    
#     # 2. VELOCIDADE (peso 3)
#     if velocidade > 0.3:
#         score += 3
#         detalhes_score['velocidade'] = 3
#     elif velocidade > 0.15:
#         score += 2
#         detalhes_score['velocidade'] = 2
#     elif velocidade > 0.05:
#         score += 1
#         detalhes_score['velocidade'] = 1
#     elif velocidade < -0.3:
#         score -= 3
#         detalhes_score['velocidade'] = -3
#     elif velocidade < -0.15:
#         score -= 2
#         detalhes_score['velocidade'] = -2
#     elif velocidade < -0.05:
#         score -= 1
#         detalhes_score['velocidade'] = -1
#     else:
#         detalhes_score['velocidade'] = 0
    
#     # 3. ACELERAÇÃO (peso 2)
#     if aceleracao > 0.2:
#         score += 2
#         detalhes_score['aceleracao'] = 2
#     elif aceleracao > 0.1:
#         score += 1.5
#         detalhes_score['aceleracao'] = 1.5
#     elif aceleracao > 0.05:
#         score += 0.5
#         detalhes_score['aceleracao'] = 0.5
#     elif aceleracao < -0.2:
#         score -= 2
#         detalhes_score['aceleracao'] = -2
#     elif aceleracao < -0.1:
#         score -= 1.5
#         detalhes_score['aceleracao'] = -1.5
#     elif aceleracao < -0.05:
#         score -= 0.5
#         detalhes_score['aceleracao'] = -0.5
#     else:
#         detalhes_score['aceleracao'] = 0
    
#     # 4. MOMENTO (peso 1.5)
#     if momento > 0.15:
#         score += 1.5
#         detalhes_score['momento'] = 1.5
#     elif momento > 0.05:
#         score += 0.75
#         detalhes_score['momento'] = 0.75
#     elif momento < -0.15:
#         score -= 1.5
#         detalhes_score['momento'] = -1.5
#     elif momento < -0.05:
#         score -= 0.75
#         detalhes_score['momento'] = -0.75
#     else:
#         detalhes_score['momento'] = 0
    
#     # 5. CRUZAMENTO (peso 1)
#     if cruzamento == 1:
#         score += 1
#         detalhes_score['cruzamento'] = 1
#     elif cruzamento == -1:
#         score -= 1
#         detalhes_score['cruzamento'] = -1
#     else:
#         detalhes_score['cruzamento'] = 0
    
#     # ================== DECISÃO FINAL ==================
#     sinais_positivos = sum(1 for v in detalhes_score.values() if v > 0)
#     sinais_negativos = sum(1 for v in detalhes_score.values() if v < 0)
#     total_sinais = len([v for v in detalhes_score.values() if v != 0])
    
#     if total_sinais > 0:
#         consistencia = abs(sinais_positivos - sinais_negativos) / total_sinais
#     else:
#         consistencia = 0
    
#     # Decisão com thresholds ajustados
#     if score >= 6 and consistencia > 0.6:
#         sinal = "CALL_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_alta"
#     elif score >= 4:
#         sinal = "CALL"
#         confianca = 0.75 + (score - 4) * 0.05
#         motivo = "tendencia_forte_alta"
#     elif score >= 2:
#         sinal = "CALL"
#         confianca = 0.60
#         motivo = "tendencia_moderada_alta"
#     elif score >= 0.5:
#         sinal = "LEVE_CALL"
#         confianca = 0.50
#         motivo = "leve_tendencia_alta"
#     elif score <= -6 and consistencia > 0.6:
#         sinal = "PUT_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_baixa"
#     elif score <= -4:
#         sinal = "PUT"
#         confianca = 0.75 + abs(score + 4) * 0.05
#         motivo = "tendencia_forte_baixa"
#     elif score <= -2:
#         sinal = "PUT"
#         confianca = 0.60
#         motivo = "tendencia_moderada_baixa"
#     elif score <= -0.5:
#         sinal = "LEVE_PUT"
#         confianca = 0.50
#         motivo = "leve_tendencia_baixa"
#     else:
#         sinal = "NEUTRO"
#         confianca = 0.30
#         motivo = "sem_tendencia_clara"
    
#     confianca = min(0.98, confianca)

#     # ================== ANÁLISE COM IA ==================
#     # Dados para análise
#     dados_mercado = {
#         'rsi_list': rsi_list,
#         'ma_list': ma_list,
#         'rsi_historico': rsi_5.tail(30).tolist(),
#         'ma_historico': ema_9_rsi.tail(30).tolist(),
#         'preco_atual': close_prices.iloc[-1]
#     }
    
#     # ✅ Usar a rede original (global)
#     #estado = rede.analisar(opcao, dados_mercado)

#     estado = rede.analisar_opcao(opcao, dados_mercado)
    
#     # Também podemos usar o ensemble em paralelo (opcional)
#     try:
#         estado_ensemble = sistema_ensemble.analisar_opcao(opcao, dados_mercado)
#         # Combinar os resultados se quiser
#         estado['ensemble'] = estado_ensemble
#     except Exception as e:
#         print(f"⚠️ Ensemble não disponível: {e}")
    
#     # ================== RETORNO ==================
#     return {
#         'decisao': estado['decisao'],
#         'sinal': sinal,
#         'confianca': round(confianca, 2),
#         'score': round(score, 2),
#         'motivo': motivo,
#         'detalhes_score': detalhes_score,
#         'slope': round(slope, 4),
#         'correlacao': round(correlacao, 3),
#         'velocidade': round(velocidade, 4),
#         'aceleracao': round(aceleracao, 4),
#         'momento': round(momento, 4),
#         'cruzamento': cruzamento,
#         'diff_atual': round(diff[-1], 4),
#         'diff_anterior': round(diff[-2], 4) if len(diff) >= 2 else None,
#         'velas_analisadas': len(diff),
#         'estado': estado,
#     }






# def sinal_opcoes_30min_melhorado(opcao):
#     """
#     Versão otimizada para opções 30min com sistema de pesos aprimorado + IA
#     """
#     symbol = ativo_principal(opcao)
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
#     if rates is None or len(rates) < 50:
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     df = pd.DataFrame(rates)
#     close_prices = df['close']
    
#     # Calcula RSI(5) e EMA(9) sobre o RSI
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
#     rsi_5 = rsi_5.dropna()
#     ema_9_rsi = ema_9_rsi.dropna()
    
#     rsi_list = rsi_5.tail(14).tolist()
#     ma_list = ema_9_rsi.tail(14).tolist()
    
#     if len(rsi_list) < 7:
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     # ================== ANÁLISE COM PESOS ==================
#     rsi = np.array(rsi_list[-7:])
#     ma = np.array(ma_list[-7:])
#     diff = rsi - ma
    
#     # ✅ NORMALIZAR O DIFF
#     diff_max = np.max(np.abs(diff))
#     if diff_max > 0:
#         diff_normalizado = diff / diff_max
#     else:
#         diff_normalizado = diff
    
#     # Usar diff_normalizado para os cálculos
#     x = np.arange(len(diff_normalizado))
#     slope, intercept = np.polyfit(x, diff_normalizado, 1)
#     correlacao = np.corrcoef(x, diff_normalizado)[0, 1] if len(diff_normalizado) > 1 else 0
    
#     # Velocidade
#     if len(diff_normalizado) >= 2:
#         velocidade = diff_normalizado[-1] - diff_normalizado[-2]
#         velocidade_media = np.mean(np.diff(diff_normalizado)) if len(diff_normalizado) > 2 else velocidade
#     else:
#         velocidade = 0
#         velocidade_media = 0
    
#     # Aceleração
#     if len(diff_normalizado) >= 3:
#         aceleracao = (diff_normalizado[-1] - diff_normalizado[-2]) - (diff_normalizado[-2] - diff_normalizado[-3])
#         aceleracao_media = np.mean(np.diff(np.diff(diff_normalizado))) if len(diff_normalizado) > 3 else aceleracao
#     else:
#         aceleracao = 0
#         aceleracao_media = 0
    
#     # Momento
#     if len(diff_normalizado) >= 3:
#         media_ultimas_3 = np.mean(diff_normalizado[-3:])
#         media_todas = np.mean(diff_normalizado)
#         momento = media_ultimas_3 - media_todas
#     else:
#         momento = 0
    
#     # Cruzamento
#     cruzamento = 0
#     if len(diff_normalizado) >= 2:
#         if diff_normalizado[-2] < 0 and diff_normalizado[-1] > 0:
#             cruzamento = 1
#         elif diff_normalizado[-2] > 0 and diff_normalizado[-1] < 0:
#             cruzamento = -1
    
#     # ================== SISTEMA DE PONTUAÇÃO ==================
#     score = 0
#     detalhes_score = {}
    
#     # 1. TENDÊNCIA (peso 4)
#     if slope > 0.3:
#         score += 4
#         detalhes_score['tendencia'] = 4
#     elif slope > 0.15:
#         score += 3
#         detalhes_score['tendencia'] = 3
#     elif slope > 0.05:
#         score += 1.5
#         detalhes_score['tendencia'] = 1.5
#     elif slope < -0.3:
#         score -= 4
#         detalhes_score['tendencia'] = -4
#     elif slope < -0.15:
#         score -= 3
#         detalhes_score['tendencia'] = -3
#     elif slope < -0.05:
#         score -= 1.5
#         detalhes_score['tendencia'] = -1.5
#     else:
#         detalhes_score['tendencia'] = 0
    
#     # Bônus por correlação forte
#     if abs(correlacao) > 0.8:
#         score += 1 if slope > 0 else -1
#         detalhes_score['correlacao'] = 1 if slope > 0 else -1
#     else:
#         detalhes_score['correlacao'] = 0
    
#     # 2. VELOCIDADE (peso 3)
#     if velocidade > 0.3:
#         score += 3
#         detalhes_score['velocidade'] = 3
#     elif velocidade > 0.15:
#         score += 2
#         detalhes_score['velocidade'] = 2
#     elif velocidade > 0.05:
#         score += 1
#         detalhes_score['velocidade'] = 1
#     elif velocidade < -0.3:
#         score -= 3
#         detalhes_score['velocidade'] = -3
#     elif velocidade < -0.15:
#         score -= 2
#         detalhes_score['velocidade'] = -2
#     elif velocidade < -0.05:
#         score -= 1
#         detalhes_score['velocidade'] = -1
#     else:
#         detalhes_score['velocidade'] = 0
    
#     # 3. ACELERAÇÃO (peso 2)
#     if aceleracao > 0.2:
#         score += 2
#         detalhes_score['aceleracao'] = 2
#     elif aceleracao > 0.1:
#         score += 1.5
#         detalhes_score['aceleracao'] = 1.5
#     elif aceleracao > 0.05:
#         score += 0.5
#         detalhes_score['aceleracao'] = 0.5
#     elif aceleracao < -0.2:
#         score -= 2
#         detalhes_score['aceleracao'] = -2
#     elif aceleracao < -0.1:
#         score -= 1.5
#         detalhes_score['aceleracao'] = -1.5
#     elif aceleracao < -0.05:
#         score -= 0.5
#         detalhes_score['aceleracao'] = -0.5
#     else:
#         detalhes_score['aceleracao'] = 0
    
#     # 4. MOMENTO (peso 1.5)
#     if momento > 0.15:
#         score += 1.5
#         detalhes_score['momento'] = 1.5
#     elif momento > 0.05:
#         score += 0.75
#         detalhes_score['momento'] = 0.75
#     elif momento < -0.15:
#         score -= 1.5
#         detalhes_score['momento'] = -1.5
#     elif momento < -0.05:
#         score -= 0.75
#         detalhes_score['momento'] = -0.75
#     else:
#         detalhes_score['momento'] = 0
    
#     # 5. CRUZAMENTO (peso 1)
#     if cruzamento == 1:
#         score += 1
#         detalhes_score['cruzamento'] = 1
#     elif cruzamento == -1:
#         score -= 1
#         detalhes_score['cruzamento'] = -1
#     else:
#         detalhes_score['cruzamento'] = 0
    
#     # ================== DECISÃO FINAL ==================
#     sinais_positivos = sum(1 for v in detalhes_score.values() if v > 0)
#     sinais_negativos = sum(1 for v in detalhes_score.values() if v < 0)
#     total_sinais = len([v for v in detalhes_score.values() if v != 0])
    
#     if total_sinais > 0:
#         consistencia = abs(sinais_positivos - sinais_negativos) / total_sinais
#     else:
#         consistencia = 0
    
#     # Decisão com thresholds ajustados
#     if score >= 6 and consistencia > 0.6:
#         sinal = "CALL_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_alta"
#     elif score >= 4:
#         sinal = "CALL"
#         confianca = 0.75 + (score - 4) * 0.05
#         motivo = "tendencia_forte_alta"
#     elif score >= 2:
#         sinal = "CALL"
#         confianca = 0.60
#         motivo = "tendencia_moderada_alta"
#     elif score >= 0.5:
#         sinal = "LEVE_CALL"
#         confianca = 0.50
#         motivo = "leve_tendencia_alta"
#     elif score <= -6 and consistencia > 0.6:
#         sinal = "PUT_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_baixa"
#     elif score <= -4:
#         sinal = "PUT"
#         confianca = 0.75 + abs(score + 4) * 0.05
#         motivo = "tendencia_forte_baixa"
#     elif score <= -2:
#         sinal = "PUT"
#         confianca = 0.60
#         motivo = "tendencia_moderada_baixa"
#     elif score <= -0.5:
#         sinal = "LEVE_PUT"
#         confianca = 0.50
#         motivo = "leve_tendencia_baixa"
#     else:
#         sinal = "NEUTRO"
#         confianca = 0.30
#         motivo = "sem_tendencia_clara"
    
#     confianca = min(0.98, confianca)

#     # ================== ANÁLISE COM IA (ENSEMBLE) ==================
#     # Dados para o sistema de IA
#     dados_mercado = {
#         'rsi_list': rsi_list,
#         'ma_list': ma_list,
#         'rsi_historico': rsi_5.tail(30).tolist(),  # Mais histórico para LSTM
#         'ma_historico': ema_9_rsi.tail(30).tolist(),
#         'preco_atual': close_prices.iloc[-1]
#     }
    
#     # Instanciar e usar o sistema de IA
#     sistema = SistemaOpcoesInteligente()
#     resultado_ia = sistema.analisar_opcao(opcao, dados_mercado)
    
#     # ================== COMBINAR RESULTADOS ==================
#     # Combinar decisão técnica com IA
#     if resultado_ia['sinal'] in ['CALL', 'CALL_FORTE']:
#         if sinal in ['CALL', 'CALL_FORTE', 'LEVE_CALL']:
#             # Alinhamento: reforça decisão
#             sinal_final = sinal
#             confianca_final = min(0.98, (confianca + resultado_ia['confianca']) / 2 + 0.1)
#             motivo_final = f"{motivo} + IA_confirma_alta"
#         elif sinal in ['PUT', 'PUT_FORTE', 'LEVE_PUT']:
#             # Divergência: usa a de maior confiança
#             if resultado_ia['confianca'] > confianca:
#                 sinal_final = resultado_ia['sinal']
#                 confianca_final = resultado_ia['confianca'] * 0.9
#                 motivo_final = f"IA_sugere_{sinal_final}_vs_tecnico_{sinal}"
#             else:
#                 sinal_final = sinal
#                 confianca_final = confianca * 0.9
#                 motivo_final = f"tecnico_sugere_{sinal}_vs_IA_{resultado_ia['sinal']}"
#         else:
#             # IA tem sinal claro, técnico neutro
#             sinal_final = resultado_ia['sinal']
#             confianca_final = resultado_ia['confianca'] * 0.85
#             motivo_final = f"IA_sugere_{sinal_final}_tecnico_neutro"
#     elif resultado_ia['sinal'] in ['PUT', 'PUT_FORTE']:
#         if sinal in ['PUT', 'PUT_FORTE', 'LEVE_PUT']:
#             sinal_final = sinal
#             confianca_final = min(0.98, (confianca + resultado_ia['confianca']) / 2 + 0.1)
#             motivo_final = f"{motivo} + IA_confirma_baixa"
#         elif sinal in ['CALL', 'CALL_FORTE', 'LEVE_CALL']:
#             if resultado_ia['confianca'] > confianca:
#                 sinal_final = resultado_ia['sinal']
#                 confianca_final = resultado_ia['confianca'] * 0.9
#                 motivo_final = f"IA_sugere_{sinal_final}_vs_tecnico_{sinal}"
#             else:
#                 sinal_final = sinal
#                 confianca_final = confianca * 0.9
#                 motivo_final = f"tecnico_sugere_{sinal}_vs_IA_{resultado_ia['sinal']}"
#         else:
#             sinal_final = resultado_ia['sinal']
#             confianca_final = resultado_ia['confianca'] * 0.85
#             motivo_final = f"IA_sugere_{sinal_final}_tecnico_neutro"
#     else:
#         # IA neutra
#         if sinal in ['CALL', 'CALL_FORTE', 'PUT', 'PUT_FORTE']:
#             sinal_final = sinal
#             confianca_final = confianca * 0.85
#             motivo_final = f"{motivo}_IA_neutra"
#         else:
#             sinal_final = "NEUTRO"
#             confianca_final = 0.20
#             motivo_final = "ambos_neutros"
    
#     # ================== RETORNO FINAL ==================
#     return {
#         'decisao': sinal_final,
#         'confianca': round(confianca_final, 2),
#         'score_tecnico': round(score, 2),
#         'score_ia': round(resultado_ia['prob_ml'], 3),
#         'motivo': motivo_final,
#         'detalhes_score': detalhes_score,
#         'slope': round(slope, 4),
#         'correlacao': round(correlacao, 3),
#         'velocidade': round(velocidade, 4),
#         'aceleracao': round(aceleracao, 4),
#         'momento': round(momento, 4),
#         'cruzamento': cruzamento,
#         'diff_atual': round(diff_normalizado[-1], 4),
#         'diff_anterior': round(diff_normalizado[-2], 4) if len(diff_normalizado) >= 2 else None,
#         'velas_analisadas': len(diff_normalizado),
#         'ia_detalhes': {
#             'sinal_original': resultado_ia['sinal'],
#             'probabilidade': resultado_ia['prob_ml'],
#             'pesos_ensemble': resultado_ia.get('pesos_ensemble', {})
#         },
#         'analise_tecnica': {
#             'sinal_original': sinal,
#             'confianca_original': confianca,
#             'consistencia': consistencia
#         }
#     }


# def sinal_opcoes_30min_melhorado(opcao):
#     """
#     Versão otimizada para opções 30min com sistema de pesos aprimorado
#     """
#     symbol = ativo_principal(opcao)
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
#     if rates is None or len(rates) < 50:
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     df = pd.DataFrame(rates)
#     close_prices = df['close']
    
#     # Calcula RSI(5) e EMA(9) sobre o RSI
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
#     rsi_5 = rsi_5.dropna()
#     ema_9_rsi = ema_9_rsi.dropna()
    
#     rsi_list = rsi_5.tail(14).tolist()
#     ma_list = ema_9_rsi.tail(14).tolist()
    
#     if len(rsi_list) < 7:
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     # ================== ANÁLISE COM PESOS ==================
#     rsi = np.array(rsi_list[-7:])
#     ma = np.array(ma_list[-7:])
#     diff = rsi - ma
    
#     # ✅ NORMALIZAR O DIFF
#     diff_max = np.max(np.abs(diff))
#     if diff_max > 0:
#         diff_normalizado = diff / diff_max
#     else:
#         diff_normalizado = diff
    
#     # Usar diff_normalizado para os cálculos
#     x = np.arange(len(diff_normalizado))
#     slope, intercept = np.polyfit(x, diff_normalizado, 1)
#     correlacao = np.corrcoef(x, diff_normalizado)[0, 1] if len(diff_normalizado) > 1 else 0
    
#     # Velocidade
#     if len(diff_normalizado) >= 2:
#         velocidade = diff_normalizado[-1] - diff_normalizado[-2]
#         velocidade_media = np.mean(np.diff(diff_normalizado)) if len(diff_normalizado) > 2 else velocidade
#     else:
#         velocidade = 0
#         velocidade_media = 0
    
#     # Aceleração
#     if len(diff_normalizado) >= 3:
#         aceleracao = (diff_normalizado[-1] - diff_normalizado[-2]) - (diff_normalizado[-2] - diff_normalizado[-3])
#         aceleracao_media = np.mean(np.diff(np.diff(diff_normalizado))) if len(diff_normalizado) > 3 else aceleracao
#     else:
#         aceleracao = 0
#         aceleracao_media = 0
    
#     # Momento
#     if len(diff_normalizado) >= 3:
#         media_ultimas_3 = np.mean(diff_normalizado[-3:])
#         media_todas = np.mean(diff_normalizado)
#         momento = media_ultimas_3 - media_todas
#     else:
#         momento = 0
    
#     # Cruzamento
#     cruzamento = 0
#     if len(diff_normalizado) >= 2:
#         if diff_normalizado[-2] < 0 and diff_normalizado[-1] > 0:
#             cruzamento = 1
#         elif diff_normalizado[-2] > 0 and diff_normalizado[-1] < 0:
#             cruzamento = -1
    
#     # ================== SISTEMA DE PONTUAÇÃO ==================
#     score = 0
#     detalhes_score = {}
    
#     # 1. TENDÊNCIA (peso 4)
#     if slope > 0.3:
#         score += 4
#         detalhes_score['tendencia'] = 4
#     elif slope > 0.15:
#         score += 3
#         detalhes_score['tendencia'] = 3
#     elif slope > 0.05:
#         score += 1.5
#         detalhes_score['tendencia'] = 1.5
#     elif slope < -0.3:
#         score -= 4
#         detalhes_score['tendencia'] = -4
#     elif slope < -0.15:
#         score -= 3
#         detalhes_score['tendencia'] = -3
#     elif slope < -0.05:
#         score -= 1.5
#         detalhes_score['tendencia'] = -1.5
#     else:
#         detalhes_score['tendencia'] = 0
    
#     # Bônus por correlação forte
#     if abs(correlacao) > 0.8:
#         score += 1 if slope > 0 else -1
#         detalhes_score['correlacao'] = 1 if slope > 0 else -1
#     else:
#         detalhes_score['correlacao'] = 0
    
#     # 2. VELOCIDADE (peso 3)
#     if velocidade > 0.3:
#         score += 3
#         detalhes_score['velocidade'] = 3
#     elif velocidade > 0.15:
#         score += 2
#         detalhes_score['velocidade'] = 2
#     elif velocidade > 0.05:
#         score += 1
#         detalhes_score['velocidade'] = 1
#     elif velocidade < -0.3:
#         score -= 3
#         detalhes_score['velocidade'] = -3
#     elif velocidade < -0.15:
#         score -= 2
#         detalhes_score['velocidade'] = -2
#     elif velocidade < -0.05:
#         score -= 1
#         detalhes_score['velocidade'] = -1
#     else:
#         detalhes_score['velocidade'] = 0
    
#     # 3. ACELERAÇÃO (peso 2)
#     if aceleracao > 0.2:
#         score += 2
#         detalhes_score['aceleracao'] = 2
#     elif aceleracao > 0.1:
#         score += 1.5
#         detalhes_score['aceleracao'] = 1.5
#     elif aceleracao > 0.05:
#         score += 0.5
#         detalhes_score['aceleracao'] = 0.5
#     elif aceleracao < -0.2:
#         score -= 2
#         detalhes_score['aceleracao'] = -2
#     elif aceleracao < -0.1:
#         score -= 1.5
#         detalhes_score['aceleracao'] = -1.5
#     elif aceleracao < -0.05:
#         score -= 0.5
#         detalhes_score['aceleracao'] = -0.5
#     else:
#         detalhes_score['aceleracao'] = 0
    
#     # 4. MOMENTO (peso 1.5)
#     if momento > 0.15:
#         score += 1.5
#         detalhes_score['momento'] = 1.5
#     elif momento > 0.05:
#         score += 0.75
#         detalhes_score['momento'] = 0.75
#     elif momento < -0.15:
#         score -= 1.5
#         detalhes_score['momento'] = -1.5
#     elif momento < -0.05:
#         score -= 0.75
#         detalhes_score['momento'] = -0.75
#     else:
#         detalhes_score['momento'] = 0
    
#     # 5. CRUZAMENTO (peso 1)
#     if cruzamento == 1:
#         score += 1
#         detalhes_score['cruzamento'] = 1
#     elif cruzamento == -1:
#         score -= 1
#         detalhes_score['cruzamento'] = -1
#     else:
#         detalhes_score['cruzamento'] = 0
    
#     # ================== DECISÃO FINAL ==================
#     sinais_positivos = sum(1 for v in detalhes_score.values() if v > 0)
#     sinais_negativos = sum(1 for v in detalhes_score.values() if v < 0)
#     total_sinais = len([v for v in detalhes_score.values() if v != 0])
    
#     if total_sinais > 0:
#         consistencia = abs(sinais_positivos - sinais_negativos) / total_sinais
#     else:
#         consistencia = 0
    
#     # Decisão com thresholds ajustados
#     if score >= 6 and consistencia > 0.6:
#         sinal = "CALL_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_alta"
#     elif score >= 4:
#         sinal = "CALL"
#         confianca = 0.75 + (score - 4) * 0.05
#         motivo = "tendencia_forte_alta"
#     elif score >= 2:
#         sinal = "CALL"
#         confianca = 0.60
#         motivo = "tendencia_moderada_alta"
#     elif score >= 0.5:
#         sinal = "LEVE_CALL"
#         confianca = 0.50
#         motivo = "leve_tendencia_alta"
#     elif score <= -6 and consistencia > 0.6:
#         sinal = "PUT_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_baixa"
#     elif score <= -4:
#         sinal = "PUT"
#         confianca = 0.75 + abs(score + 4) * 0.05
#         motivo = "tendencia_forte_baixa"
#     elif score <= -2:
#         sinal = "PUT"
#         confianca = 0.60
#         motivo = "tendencia_moderada_baixa"
#     elif score <= -0.5:
#         sinal = "LEVE_PUT"
#         confianca = 0.50
#         motivo = "leve_tendencia_baixa"
#     else:
#         sinal = "NEUTRO"
#         confianca = 0.30
#         motivo = "sem_tendencia_clara"
    
#     confianca = min(0.98, confianca)

#     # Dados para análise (usando os valores originais)
#     dados_mercado = {
#         'rsi_list': rsi_list,
#         'ma_list': ma_list,
#         'preco_atual': close_prices.iloc[-1]
#     }
    
#     # Analisar com a rede neural
#     estado = rede.analisar(opcao, dados_mercado)
    
#     return {
#         'decisao': estado['decisao'],
#         'sinal': sinal,
#         'confianca': round(confianca, 2),
#         'score': round(score, 2),  # <-- Score normalizado!
#         'motivo': motivo,
#         'detalhes_score': detalhes_score,
#         'slope': round(slope, 4),
#         'correlacao': round(correlacao, 3),
#         'velocidade': round(velocidade, 4),
#         'aceleracao': round(aceleracao, 4),
#         'momento': round(momento, 4),
#         'cruzamento': cruzamento,
#         'diff_atual': round(diff_normalizado[-1], 4),
#         'diff_anterior': round(diff_normalizado[-2], 4) if len(diff_normalizado) >= 2 else None,
#         'velas_analisadas': len(diff_normalizado),
#         'estado': estado,
#     }


# def sinal_opcoes_30min_melhorado(opcao):
#     """
#     Versão otimizada para opções 30min com sistema de pesos aprimorado
#     Usa 5-7 velas para equilíbrio entre velocidade e confiabilidade
#     """
#     symbol = ativo_principal(opcao)
#     timeframe = mt5.TIMEFRAME_M30
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
    
#     if rates is None or len(rates) < 50:
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     df = pd.DataFrame(rates)
#     close_prices = df['close']
    
#     # Calcula RSI(5) e EMA(9) sobre o RSI
#     rsi_5 = calculate_rsi(close_prices, period=5)
#     ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
#     rsi_5 = rsi_5.dropna()
#     ema_9_rsi = ema_9_rsi.dropna()
    
#     rsi_list = rsi_5.tail(14).tolist()
#     ma_list = ema_9_rsi.tail(14).tolist()
    
#     if len(rsi_list) < 7:  # Aumentado para 7 para melhor análise
#         return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
#     # ================== ANÁLISE COM PESOS ==================
    
#     # Converter para numpy (usando 7 velas para melhor análise)
#     rsi = np.array(rsi_list[-7:])
#     ma = np.array(ma_list[-7:])
#     diff = rsi - ma
    
#     # ----- 1. Análise de Tendência (peso 4) -----
#     x = np.arange(len(diff))
#     slope, intercept = np.polyfit(x, diff, 1)
    
#     # Correlação (força da tendência)
#     correlacao = np.corrcoef(x, diff)[0, 1] if len(diff) > 1 else 0
    
#     # ----- 2. Velocidade (peso 3) -----
#     if len(diff) >= 2:
#         velocidade = diff[-1] - diff[-2]
#         velocidade_media = np.mean(np.diff(diff)) if len(diff) > 2 else velocidade
#     else:
#         velocidade = 0
#         velocidade_media = 0
    
#     # ----- 3. Aceleração (peso 2) -----
#     if len(diff) >= 3:
#         aceleracao = (diff[-1] - diff[-2]) - (diff[-2] - diff[-3])
#         aceleracao_media = np.mean(np.diff(np.diff(diff))) if len(diff) > 3 else aceleracao
#     else:
#         aceleracao = 0
#         aceleracao_media = 0
    
#     # ----- 4. Momento (peso 1.5) -----
#     # Comparação com média recente
#     if len(diff) >= 3:
#         media_ultimas_3 = np.mean(diff[-3:])
#         media_todas = np.mean(diff)
#         momento = media_ultimas_3 - media_todas
#     else:
#         momento = 0
    
#     # ----- 5. Cruzamento (peso 1) -----
#     # Verifica se está cruzando a MA
#     cruzamento = 0
#     if len(diff) >= 2:
#         if diff[-2] < 0 and diff[-1] > 0:
#             cruzamento = 1  # Cruzamento de alta
#         elif diff[-2] > 0 and diff[-1] < 0:
#             cruzamento = -1  # Cruzamento de baixa
    
#     # ================== SISTEMA DE PONTUAÇÃO ==================
    
#     score = 0
#     detalhes_score = {}
    
#     # 1. TENDÊNCIA (peso 4) - mais importante
#     if slope > 0.3:
#         score += 4
#         detalhes_score['tendencia'] = 4
#     elif slope > 0.15:
#         score += 3
#         detalhes_score['tendencia'] = 3
#     elif slope > 0.05:
#         score += 1.5
#         detalhes_score['tendencia'] = 1.5
#     elif slope < -0.3:
#         score -= 4
#         detalhes_score['tendencia'] = -4
#     elif slope < -0.15:
#         score -= 3
#         detalhes_score['tendencia'] = -3
#     elif slope < -0.05:
#         score -= 1.5
#         detalhes_score['tendencia'] = -1.5
#     else:
#         detalhes_score['tendencia'] = 0
    
#     # Bônus por correlação forte
#     if abs(correlacao) > 0.8:
#         score += 1 if slope > 0 else -1
#         detalhes_score['correlacao'] = 1 if slope > 0 else -1
#     else:
#         detalhes_score['correlacao'] = 0
    
#     # 2. VELOCIDADE (peso 3)
#     if velocidade > 0.3:
#         score += 3
#         detalhes_score['velocidade'] = 3
#     elif velocidade > 0.15:
#         score += 2
#         detalhes_score['velocidade'] = 2
#     elif velocidade > 0.05:
#         score += 1
#         detalhes_score['velocidade'] = 1
#     elif velocidade < -0.3:
#         score -= 3
#         detalhes_score['velocidade'] = -3
#     elif velocidade < -0.15:
#         score -= 2
#         detalhes_score['velocidade'] = -2
#     elif velocidade < -0.05:
#         score -= 1
#         detalhes_score['velocidade'] = -1
#     else:
#         detalhes_score['velocidade'] = 0
    
#     # 3. ACELERAÇÃO (peso 2)
#     if aceleracao > 0.2:
#         score += 2
#         detalhes_score['aceleracao'] = 2
#     elif aceleracao > 0.1:
#         score += 1.5
#         detalhes_score['aceleracao'] = 1.5
#     elif aceleracao > 0.05:
#         score += 0.5
#         detalhes_score['aceleracao'] = 0.5
#     elif aceleracao < -0.2:
#         score -= 2
#         detalhes_score['aceleracao'] = -2
#     elif aceleracao < -0.1:
#         score -= 1.5
#         detalhes_score['aceleracao'] = -1.5
#     elif aceleracao < -0.05:
#         score -= 0.5
#         detalhes_score['aceleracao'] = -0.5
#     else:
#         detalhes_score['aceleracao'] = 0
    
#     # 4. MOMENTO (peso 1.5)
#     if momento > 0.15:
#         score += 1.5
#         detalhes_score['momento'] = 1.5
#     elif momento > 0.05:
#         score += 0.75
#         detalhes_score['momento'] = 0.75
#     elif momento < -0.15:
#         score -= 1.5
#         detalhes_score['momento'] = -1.5
#     elif momento < -0.05:
#         score -= 0.75
#         detalhes_score['momento'] = -0.75
#     else:
#         detalhes_score['momento'] = 0
    
#     # 5. CRUZAMENTO (peso 1)
#     if cruzamento == 1:
#         score += 1
#         detalhes_score['cruzamento'] = 1
#     elif cruzamento == -1:
#         score -= 1
#         detalhes_score['cruzamento'] = -1
#     else:
#         detalhes_score['cruzamento'] = 0
    
#     # ================== DECISÃO FINAL ==================
    
#     # Calcular confiança baseada na consistência dos sinais
#     sinais_positivos = sum(1 for v in detalhes_score.values() if v > 0)
#     sinais_negativos = sum(1 for v in detalhes_score.values() if v < 0)
#     total_sinais = len([v for v in detalhes_score.values() if v != 0])
    
#     if total_sinais > 0:
#         consistencia = abs(sinais_positivos - sinais_negativos) / total_sinais
#     else:
#         consistencia = 0
    
#     # Decisão com thresholds ajustados
#     if score >= 6 and consistencia > 0.6:
#         sinal = "CALL_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_alta"
#     elif score >= 4:
#         sinal = "CALL"
#         confianca = 0.75 + (score - 4) * 0.05
#         motivo = "tendencia_forte_alta"
#     elif score >= 2:
#         sinal = "CALL"
#         confianca = 0.60
#         motivo = "tendencia_moderada_alta"
#     elif score >= 0.5:
#         sinal = "LEVE_CALL"
#         confianca = 0.50
#         motivo = "leve_tendencia_alta"
#     elif score <= -6 and consistencia > 0.6:
#         sinal = "PUT_FORTE"
#         confianca = 0.92
#         motivo = "tendencia_muito_forte_baixa"
#     elif score <= -4:
#         sinal = "PUT"
#         confianca = 0.75 + abs(score + 4) * 0.05
#         motivo = "tendencia_forte_baixa"
#     elif score <= -2:
#         sinal = "PUT"
#         confianca = 0.60
#         motivo = "tendencia_moderada_baixa"
#     elif score <= -0.5:
#         sinal = "LEVE_PUT"
#         confianca = 0.50
#         motivo = "leve_tendencia_baixa"
#     else:
#         sinal = "NEUTRO"
#         confianca = 0.30
#         motivo = "sem_tendencia_clara"
    
#     # Confiança máxima
#     confianca = min(0.98, confianca)

#     # Dados para análise
#     dados_mercado = {
#         'rsi_list': rsi_list,
#         'ma_list': ma_list,
#         'preco_atual': close_prices.iloc[-1]
#     }
    
#     # Analisar com a rede neural
#     estado = rede.analisar(opcao, dados_mercado)
    
#     #return estado['decisao']

    
#     return {
#         'decisao':estado['decisao'],
#         'sinal': sinal,
#         'confianca': round(confianca, 2),
#         'score': round(score, 2),
#         'motivo': motivo,
#         'detalhes_score': detalhes_score,
#         'slope': round(slope, 4),
#         'correlacao': round(correlacao, 3),
#         'velocidade': round(velocidade, 4),
#         'aceleracao': round(aceleracao, 4),
#         'momento': round(momento, 4),
#         'cruzamento': cruzamento,
#         'diff_atual': round(diff[-1], 4),
#         'diff_anterior': round(diff[-2], 4) if len(diff) >= 2 else None,
#         'velas_analisadas': len(diff),
#         'estado':estado,
#     }

# Se você quiser algo ainda mais simples para usar diretamente:

def is_proibida(status, tipo, *args):
    """Verifica se é proibida em uma linha"""
    combinacoes = {
        'proibidas1': [
            ('compra','call','LV',"R",'negativa'), ('venda','call','G','T^','positiva'),
            ('compra','put','T^','G','positiva'), ('venda','put','R','LV','negativa')
        ],
        'proibidas2': [
            ('compra','call','LV','negativa'), ('venda','call','T^','positiva'),
            ('compra','put','T^','positiva'), ('venda','put','LV','negativa')
        ],
        
        
        'proibidas3': [
        ('compra','call','negativa'), ('venda','call','positiva'),
        ('compra','put','positiva'), ('venda','put','negativa')
        ],
        'proibidas4': [
            
            ('compra','call','LV'), ('venda','call','T^'),
            ('compra','put','T^'), ('venda','put','LV')
        
        ]
    }
    
    op = tuple([status, tipo] + list(args))
    
    for nome, proibidas in combinacoes.items():
        for p in proibidas:
            if all(op[i] == p[i] for i in range(min(len(op), len(p)))):
                return True, nome
    
    return False, None

# Versão mais simples ainda - retorna direto a mensagem
# def is_proibida(ativo, status, tipo, *args):
#     combinacoes = {
#         'proibidas1': [
#             ('compra','call','LV',"R",'negativa'), ('venda','call','G','T^','positiva'),
#             ('compra','put','T^','G','positiva'), ('venda','put','R','LV','negativa')
#         ],
#         'proibidas2': [
#             ('compra','call','LV','negativa'), ('venda','call','T^','positiva'),
#             ('compra','put','T^','positiva'), ('venda','put','LV','negativa')
#         ],
#         'proibidas3': [
#             ('compra','call','LV'), ('venda','call','T^'),
#             ('compra','put','T^'), ('venda','put','LV')
#         ],
#         'proibidas4': [
#             ('compra','call','negativa'), ('venda','call','positiva'),
#             ('compra','put','positiva'), ('venda','put','negativa')
#         ]
#     }
    
#     op = tuple([status, tipo] + list(args))
    
#     for nome, proibidas in combinacoes.items():
#         for p in proibidas:
#             if len(op) >= len(p) and all(op[i] == p[i] for i in range(len(p))):
#                 return f"⚠️ {ativo} em {nome}"
    
#     return f"✅ {ativo} - Operação permitida"

# # Uso direto:









def determinar_direcao_RSI(opcao, qt):
    """
    felipe
    Analisa RSI(5) e sua EMA(9) + tipo da vela atual.
    Retorna direção, impulso, cruzamentos, tendência da diferença e recomendação.
    """
    # Obtém o símbolo
    limiar_aprox=1.5
    symbol = ativo_principal(opcao)
    #symbol = "VALE3"  # fallback
    prefixo = symbol.upper()[:4]
    # Inicializa dicionário para esse prefixo, se não existir
    if prefixo not in tickers_STATUS:
        tickers_STATUS[prefixo] = {}
        tickers_STATUS[prefixo]["trivelas"] = None   
    

    
    timeframe = mt5.TIMEFRAME_M30
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)

    acho=None
    if rates is None or len(rates) < 50:
        return "erro", "dados_insuficientes", [], "indefinida", "AGUARDAR (dados insuficientes)"

    df = pd.DataFrame(rates)
    close_prices = df['close']

    # ----- Dados da última vela -----
    # Após obter df e antes de calcular RSI
    ultima_vela = df.iloc[-1]
    
    open_ = ultima_vela['open']
    high_ = ultima_vela['high']
    low_ = ultima_vela['low']
    close_ = ultima_vela['close']
    
    # candleSize= high_-low_
    # pav_sombra=""
    # maxPavioSombra=0.3
    # volume = abs(open_ - close_)
    # if open_ < close_:               # Vela de alta
    #     sombra = abs(low_ - open_)   # equivalente a open_ - low_
    #     pavio  = abs(close_ - high_) # equivalente a high_ - close_
    # elif open_ > close_:             # Vela de baixa
    #     sombra = abs(low_ - close_)  # equivalente a close_ - low_
    #     pavio  = abs(high_ - open_)  # equivalente a high_ - open_
    # else:                            # Vela de corpo nulo (doji)
    #     sombra = 0.0
    #     pavio  = 0.0
   
    # pav_sombra = "LV" if pavio > candleSize * maxPavioSombra else ("T^" if sombra > candleSize * maxPavioSombra else "")   
    # #tickers_STATUS[prefixo]["trivelas"] =  vela_volume(df,2),vela_volume(df,1), vela_volume(df,0)
    #     # Inicialização
    threshold_pavio=0.66 
    threshold_sombra=0.66

    
    candle_size = high_ - low_
    corpo = abs(close_ - open_)
    
    if open_ < close_:  # alta
        sombra = open_ - low_
        pavio  = high_ - close_
    elif open_ > close_:  # baixa
        sombra = close_ - low_
        pavio  = high_ - open_
    else:  # doji
        sombra = pavio = 0.0
    
    if  corpo > 0:
        rel_pavio = pavio / corpo
        rel_sombra = sombra / corpo
    else:
        rel_pavio = pavio / candle_size if candle_size > 0 else 0
        rel_sombra = sombra / candle_size if candle_size > 0 else 0
    
    if rel_pavio >= threshold_pavio  and pavio> sombra:
        pav_sombra = "lv" if rel_pavio < 1 else "LV"
    elif rel_sombra >= threshold_sombra and pavio< sombra :
        pav_sombra = "t^" if rel_sombra < 1 else "T^"
    else:
        pav_sombra= ""








    if tickers_STATUS[prefixo].get("inverteu") is None:
        tickers_STATUS[prefixo]["inverteu"] = False

    if tickers_STATUS[prefixo].get("sentido") is None:
        tickers_STATUS[prefixo]["sentido"] = ""

    
    if tickers_STATUS[prefixo].get("trivelas") is None:
        tickers_STATUS[prefixo]["trivelas"] = (
            vela_volume(df, 2),
            vela_volume(df, 1),
            vela_volume(df, 0)

        )
        tickers_STATUS[prefixo]["sentido"] ="positiva" if ( vela_volume(df, 0)   or '').upper() == "G" else "negativa"     
    else:
        tripla_antiga = tickers_STATUS[prefixo]["trivelas"]
        
        v2_nova = vela_volume(df, 2)
        v1_nova = vela_volume(df, 1)
        v0_nova = vela_volume(df, 0)
        tickers_STATUS[prefixo]["sentido"] ="positiva" if ( vela_volume(df, 0)   or '').upper() == "G" else "negativa"
        # =============================================
        # 1. DETECTAR SE UMA NOVA VELA COMEÇOU (mudou v2 ou v1)
        # =============================================
        if v2_nova != tripla_antiga[0] or v1_nova != tripla_antiga[1]:
            # Uma nova vela acabou de fechar e uma nova começou
            tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
            # Resetar o flag de inversão, pois a nova vela ainda não mostrou reversão
            tickers_STATUS[prefixo]["inverteu"] = False
            tickers_STATUS[prefixo]["sentido"] = False
            print(f"🆕 Nova vela em {prefixo}. Flag 'inverteu' resetado para False.")
            # Opcional: verificar se a vela que fechou teve reversão? 
            # Mas você quer apenas o estado da vela atual, então ignore.
        
        # =============================================
        # 2. DETECTAR MUDANÇA NA VELA ATUAL (v0)
        # =============================================
        elif v0_nova != tripla_antiga[2]:
            # A vela atual mudou de cor (ex: 'g' -> 'R')
            tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
            
            reversao = verificar_reversao(tripla_antiga[2], v0_nova)
            
            if reversao:
                tickers_STATUS[prefixo]["inverteu"] = True
                tickers_STATUS[prefixo]["sentido"] = reversao
                print(f"⚠️ REVERSÃO na vela ATUAL de {prefixo}: {tripla_antiga[2]} -> {v0_nova}")
            else:
                # Mudou mas não inverteu (ex: 'g' -> 'g'? não entraria porque mudou? 
                # Se mudou mas não inverteu, pode ser algo como 'g' para 'G'? Ajuste sua lógica)
                # Neste caso, você pode manter o flag como está (não resetar)
                print(f"🔄 Vela atual mudou sem reversão: {tripla_antiga[2]} -> {v0_nova}")
        
    
    
    #s = 'negativa' if (pav_sombra != "T^" and tickers_STATUS[prefixo]["sentido"] == 'negativa') else ('positiva' if pav_sombra != "LV" and tickers_STATUS[prefixo]["sentido"] == 'positiva' else 'neutra')
    #tickers_STATUS[prefixo]["sentido"]=s

    #------------------
    
    
    # if tickers_STATUS[prefixo].get("inverteu") is None:
    #     tickers_STATUS[prefixo]["inverteu"] = False

    # if tickers_STATUS[prefixo].get("trivelas") is None:
    #     # Guarda a tripla (vela2, vela1, vela0) – vela0 é a atual
    #     tickers_STATUS[prefixo]["trivelas"] = (
    #         vela_volume(df, 2),
    #         vela_volume(df, 1),
    #         vela_volume(df, 0)
    #     )
    # else:
    #     tripla_antiga = tickers_STATUS[prefixo]["trivelas"]
        
    #     v2_nova = vela_volume(df, 2)
    #     v1_nova = vela_volume(df, 1)
    #     v0_nova = vela_volume(df, 0)
        
    #     # Verifica se a vela atual (v0) mudou em relação à anterior (tripla_antiga[2])
    #     if v0_nova != tripla_antiga[2]:
    #         # A vela atual mudou de valor! (ex: 'g' -> 'R')
    #         tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
    #         tickers_STATUS[prefixo]["inverteu"] = False
    #         # Verifica se essa mudança é uma reversão (positiva -> negativa ou vice-versa)
    #         reversao = verificar_reversao(tripla_antiga[2], v0_nova)
    #         #tickers_STATUS[prefixo]["inverteu"] = reversao
            
    #         # Mensagem de alerta
    #         if reversao:
    #             tickers_STATUS[prefixo]["inverteu"] = True
    #             print(f"⚠️ REVERSÃO na vela ATUAL de {prefixo}: {tripla_antiga[2]} -> {v0_nova}"*100)
    #         else:
    #             print(f"🔄 Vela atual mudou (sem reversão) em {prefixo}: {tripla_antiga[2]} -> {v0_nova}")
        
        # Se a vela atual não mudou, nada faz (mantém inverteu inalterado)



    # i_tri=""
    # if tickers_STATUS[prefixo].get("inverteu") is None:
    #     tickers_STATUS[prefixo]["inverteu"]= False
    
    # if tickers_STATUS[prefixo].get("trivelas") is None:
    # # Inicializa com a tripla atual
    #     tickers_STATUS[prefixo]["trivelas"] = (
    #         vela_volume(df, 2),
    #         vela_volume(df, 1),
    #         vela_volume(df, 0)
    # )
    #     tickers_STATUS[prefixo]["ultima_msg"] = "🔷 Inicializado"
    #     print(f"🔷 Inicializado {prefixo}: {tickers_STATUS[prefixo]['trivelas']}")
    # # Não há o que processar nesta chamada, sai ou continua? 
    # # Se quiser continuar, precisa definir tripla_antiga como a atual
    #     tripla_antiga = tickers_STATUS[prefixo]["trivelas"]
    # else:
    #     tripla_antiga = tickers_STATUS[prefixo]["trivelas"]
    
    
    #     #print (tripla_antiga)
    #     v2_nova = vela_volume(df, 2)
    #     v1_nova = vela_volume(df, 1)
    #     v0_nova = vela_volume(df, 0)

    #     # Verifica se houve nova vela (mudança nas posições 2 ou 1)
    #     i_tri=""
    #     reversao = False  # assume que não houve reversão
    #     if v2_nova != tripla_antiga[0] or v1_nova != tripla_antiga[1]:
    #         # Nova vela formada: atualiza a tripla
    #         tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
    #         i_tri=f"🆕 Nova vela detectada em {prefixo}"
    #         #print(i_tri)
    #         # Opcional: verificar reversão na vela que acabou de fechar (antiga vela0)
    #         reversao = verificar_reversao(tripla_antiga[2], v0_nova)  # função auxiliar
    #         if reversao:
    #             i_tri=f"⚠️ Reversão detectada na vela anterior de {prefixo}: {reversao}"

    #            # print(i_tri)

    #     # Se a vela2 e vela1 são as mesmas, mas a vela0 mudou (vela atual em formação)
    #     elif v0_nova != tripla_antiga[2]:
    #         tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
    #         i_tri=(f"🔄 Vela atual mudou em {prefixo}: {tripla_antiga[2]} -> {v0_nova}")
    #         #print(i_tri)
    #         # Verifica se foi de positiva para negativa (ou vice-versa)
    #         reversao = verificar_reversao(tripla_antiga[2], v0_nova)
    #         if reversao:
    #             i_tri=(f"⚠️ Reversão na vela atual de {prefixo}: {reversao}")
    #             tickers_STATUS[prefixo]["inverteu"]= i_tri
    #             #print(i_tri)

    #     if reversao:
    #         tickers_STATUS[prefixo]["inverteu"] = True   # ou "reversao"
    #     else:
    #         tickers_STATUS[prefixo]["inverteu"] = False  # ou "" (string vazia)
    
    # print(i_tri, tripla_antiga)
    
    
    
    # else:
    #     bracket = tickers_STATUS[prefixo]["trivelas"]
    #     primeira_letra = bracket[2] if bracket and len(bracket) >= 3 else None
    #     segunda_letra = bracket[1] if bracket and len(bracket) >= 3 else None 
    #     terceira_letra = bracket[0] if bracket and len(bracket) >= 3 else None
    #     if vela_volume(df,2)!= terceira_letra and vela_volume(df,1)!= segunda_letra:
    #         tickers_STATUS[prefixo]["trivelas"] =  vela_volume(df,2),vela_volume(df,1), vela_volume(df,0)

    #     elif vela_volume(df,2)== terceira_letra and vela_volume(df,1)== segunda_letra:    
    #         if primeira_letra!= vela_volume(df,0): print ("mudou")
        
    
    #tickers_STATUS[prefixo]["teste"] = tickers_STATUS[prefixo]["trivelas"][:2]
    #bracket = tickers_STATUS[prefixo]["trivelas"]
    #segunda_letra = bracket[1] if bracket and len(bracket) >= 3 else None
    #-----------------------------------------------------------------------------
    
    # if tickers_STATUS[prefixo]["trivelas"] is None:
    #     tickers_STATUS[prefixo]["trivelas"] = (vela_volume(df,2), vela_volume(df,1), vela_volume(df,0))
    
    # else:
    #     tripla_antiga = tickers_STATUS[prefixo]["trivelas"]
    #     v2_nova = vela_volume(df, 2)
    #     v1_nova = vela_volume(df, 1)
    #     v0_nova = vela_volume(df, 0)

    #     # Verifica se houve nova vela (mudança nas posições 2 ou 1)
    #     if v2_nova != tripla_antiga[0] or v1_nova != tripla_antiga[1]:
    #         # Nova vela formada: atualiza a tripla
    #         tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
    #         print(f"🆕 Nova vela detectada em {prefixo}")
    #         # Opcional: verificar reversão na vela que acabou de fechar (antiga vela0)
    #         reversao = verificar_reversao(tripla_antiga[2], v0_nova)  # função auxiliar
    #         if reversao:
    #             print(f"⚠️ Reversão detectada na vela anterior de {prefixo}: {reversao}")

    #     # Se a vela2 e vela1 são as mesmas, mas a vela0 mudou (vela atual em formação)
    #     elif v0_nova != tripla_antiga[2]:
    #         tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
    #         print(f"🔄 Vela atual mudou em {prefixo}: {tripla_antiga[2]} -> {v0_nova}")

    #         # Verifica se foi de positiva para negativa (ou vice-versa)
    #         reversao = verificar_reversao(tripla_antiga[2], v0_nova)
    #         if reversao:
    #             print(f"⚠️ Reversão na vela atual de {prefixo}: {reversao}")

    
    # # Parâmetros ajustáveis
    # SOMBRA_MAX_PURA = 0.30      # 30% do corpo
    # SOMBRA_OPOSTA_MAX = 0.03    # 10% do corpo (para ser considerado puro)

    # if close_ > open_:
    #     corpo = close_ - open_
    #     sombra_inferior = open_ - low_
    #     sombra_superior = high_ - close_
    #     # Vela positiva pura: sombra inferior pequena E sombra superior pequena
    #     if sombra_inferior <= corpo * SOMBRA_MAX_PURA and sombra_superior <= corpo * SOMBRA_OPOSTA_MAX:
    #         tipo_vela = "positiva pura"
    #     else:
    #         tipo_vela = "positiva mista"

    # elif close_ < open_:
    #     corpo = open_ - close_
    #     sombra_superior = high_ - open_
    #     sombra_inferior = close_ - low_
    #     # Vela negativa pura: sombra superior pequena E sombra inferior pequena
    #     if sombra_superior <= corpo * SOMBRA_MAX_PURA and sombra_inferior <= corpo * SOMBRA_OPOSTA_MAX:
    #         tipo_vela = "negativa pura"
    #     else:
    #         tipo_vela = "negativa mista"

    # else:
    #     tipo_vela = "neutra"


    
    if close_ > open_:
        corpo = close_ - open_
        sombra_inferior = open_ - low_
        if sombra_inferior < corpo and not tickers_STATUS[prefixo]["inverteu"]:

        #if sombra_inferior < corpo:
            tipo_vela = "positiva pura"
        else:
            tipo_vela = "positiva mista"
    elif close_ < open_:
        corpo = open_ - close_
        sombra_superior = high_ - open_
        if sombra_superior < corpo and not tickers_STATUS[prefixo]["inverteu"]:
        #if sombra_superior < corpo:
            tipo_vela = "negativa pura"
        else:
            tipo_vela = "negativa mista"
    else:
        tipo_vela = "neutra"



    # Calcula RSI(5) e EMA(9) sobre o RSI
    rsi_5 = calculate_rsi(close_prices, period=5)
    ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()

    rsi_5 = rsi_5.dropna()
    ema_9_rsi = ema_9_rsi.dropna()

    rsi_list = rsi_5.tail(qt).tolist()
    ma_list = ema_9_rsi.tail(qt).tolist()

    if len(rsi_list) < qt:
        return "dados_insuficientes", "poucos_dados", [], "indefinida", "AGUARDAR (poucos dados)"

    
    
    

    rsi = np.array(rsi_list)
    ma = np.array(ma_list)

    # ----- 1. Cruzamentos (vetorizado) -----
    diff = rsi - ma
    sinal_anterior = np.sign(diff[:-1])
    sinal_atual = np.sign(diff[1:])

    cruzamentos = []
    # Adiciona os cruzamentos de Alta
    for i in np.where((sinal_anterior == -1) & (sinal_atual == 1))[0]:
        cruzamentos.append(f"Alta entre {i} e {i+1}")
    # Adiciona os cruzamentos de Baixa
    for i in np.where((sinal_anterior == 1) & (sinal_atual == -1))[0]:
        cruzamentos.append(f"Baixa entre {i} e {i+1}")

    # ----- 2. Tendência com loop único (mais rápido) -----
    variacoes = np.diff(diff)

    # Detecta padrão em uma única passagem
    if len(variacoes) > 0:
        primeiro = variacoes[0]
        if primeiro > 0:
            tendencia_diff = "crescente" if np.all(variacoes > 0) else "flutuante"
        elif primeiro < 0:
            tendencia_diff = "decrescente" if np.all(variacoes < 0) else "flutuante"
        else:
            tendencia_diff = "estável" if np.all(variacoes == 0) else "flutuante"
    else:
        tendencia_diff = "estável"  # apenas 1 ponto


   

    # Converter para arrays numpy
    rsi = np.array(rsi_list)
    ma = np.array(ma_list)
    diff = rsi - ma

    # ----- 3. Classificação do impulso (mais elegante) -----
    diff_atual = diff[-1]

    # Mapeamento de posição (mais rápido que if/elif)
    posicao = {
        1: "acima_da_MA",
        -1: "abaixo_da_MA",
        0: "neutro"
    }[np.sign(diff_atual).item()]

    # Mapeamento de impulso usando dicionário aninhado
    impulso_map = {
        "crescente": {
            "negativo": "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)",
            "positivo": "ACELERAÇÃO DE ALTA (RSI se afastando para cima)"
        },
        "decrescente": {
            "positivo": "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)",
            "negativo": "ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)"
        },
        "estável": {
            "default": "IMPULSO NEUTRO (diferença constante)"
        },
        "flutuante": {
            "default": "IMPULSO INDEFINIDO (oscilação sem direção clara)"
        }
    }

    # Determinar impulso com dicionário
    if tendencia_diff in ["crescente", "decrescente"]:
        sinal = "positivo" if diff_atual > 0 else "negativo"
        impulso = impulso_map[tendencia_diff][sinal]
        acho = 'up' if (tendencia_diff == "crescente" and tipo_vela == 'positiva pura') else \
            'down' if (tendencia_diff == "decrescente" and tipo_vela == 'negativa pura') else None
    else:
        impulso = impulso_map[tendencia_diff]["default"]
        acho = None

    # ----- 4. Direção final -----
    rsi_atual = rsi[-1]
    ma_atual = ma[-1]



    
    # ----- 4. Direção final -----
    rsi_atual = rsi_list[-1]
    ma_atual = ma_list[-1]

    # if rsi_atual > ma_atual:
    #     direcao = "vai subir"
    # elif rsi_atual < ma_atual:
    #     direcao = "vai descer"
    # else:
    #     direcao = "parado"

    
    if rsi_atual < ma_atual and tendencia_diff == "crescente":
        if diff_atual > -limiar_aprox:
            direcao = "vai subir "
        else:
            direcao = "vai descer "
    elif rsi_atual > ma_atual and tendencia_diff == "decrescente":
        if diff_atual < limiar_aprox:
            direcao = "vai descer "
        else:
            direcao = "vai subir "
    else:
        if rsi_atual > ma_atual:
            direcao = "vai subir"
        elif rsi_atual < ma_atual:
            direcao = "vai descer"
        else:
            direcao = "parado"



    
    
    
    
    
    
    
    
    
    # ----- 5. Recomendação baseada em força (com trava de impulso indefinido) -----
    recomendacao = "AGUARDAR"

    if impulso == "IMPULSO INDEFINIDO (oscilação sem direção clara)":
        recomendacao = "AGUARDAR (impulso indefinido, risco elevado)"
    else:
        forca_alta = 0
        if direcao == "vai subir":
            if impulso in ["ACELERAÇÃO DE ALTA (RSI se afastando para cima)",
                           "APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)"]:
                forca_alta += 2
            if "Alta" in str(cruzamentos):
                forca_alta += 2
            if tendencia_diff == "crescente":
                forca_alta += 1
            if diff_atual > 5:
                forca_alta += 1

        forca_baixa = 0
        if direcao == "vai descer":
            if impulso in ["ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)",
                           "APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)"]:
                forca_baixa += 2
            if "Baixa" in str(cruzamentos):
                forca_baixa += 2
            if tendencia_diff == "decrescente":
                forca_baixa += 1
            if diff_atual < -5:
                forca_baixa += 1

        if forca_alta >= 3:
            recomendacao = "COMPRA DE CALL"
        elif forca_alta >= 2:
            recomendacao = "COMPRA DE CALL (moderada)"
        elif forca_baixa >= 3:
            recomendacao = "COMPRA DE PUT"
        elif forca_baixa >= 2:
            recomendacao = "COMPRA DE PUT (moderada)"
        elif forca_baixa >= 1 and direcao == "vai descer":
            recomendacao = "VENDA DE CALL (estratégia conservadora)"
        elif forca_alta >= 1 and direcao == "vai subir":
            recomendacao = "VENDA DE PUT (estratégia conservadora)"
        else:
            recomendacao = "AGUARDAR"

        if recomendacao == "AGUARDAR" and cruzamentos:
            if "Alta" in str(cruzamentos[-1]):
                recomendacao = "COMPRA DE CALL (cruzamento recente)"
            elif "Baixa" in str(cruzamentos[-1]):
                recomendacao = "COMPRA DE PUT (cruzamento recente)"

    # ----- 6. Verificação de conflito com a última vela -----
    # # Impede recomendação de baixa em vela positiva
    # if tipo_vela == "positiva" and ("VENDA DE CALL" in recomendacao or "COMPRA DE PUT" in recomendacao):
    #     recomendacao = "AGUARDAR (vela positiva conflita com sinal de baixa)"
    # # Impede recomendação de alta em vela negativa
    # elif tipo_vela == "negativa" and ("COMPRA DE CALL" in recomendacao or "VENDA DE PUT" in recomendacao):
    #     recomendacao = "AGUARDAR (vela negativa conflita com sinal de alta)"
    # ----- 6. Verificação com base no tipo detalhado da vela -----
    if tipo_vela == "positiva pura":
        if "VENDA DE CALL" in recomendacao or "COMPRA DE PUT" in recomendacao:
            recomendacao = "AGUARDAR (vela positiva pura, não opere baixa)"
    elif tipo_vela == "negativa pura":
        if "COMPRA DE CALL" in recomendacao or "VENDA DE PUT" in recomendacao:
            recomendacao = "AGUARDAR (vela negativa pura, não opere alta)"
    elif tipo_vela in ["positiva mista", "negativa mista"]:
        # Mantém a recomendação, mas pode adicionar um aviso
        recomendacao += " (vela mista - cautela)"
    # vela neutra: mantém recomendação original
    
    
    
    
    
    
    # Se a vela for neutra, mantém a recomendação original
    if houve_quebra_lateralizacao(df, n=3, tolerancia=0.005):
        print("Houve quebra da lateralização!")

    resultado = detectar_lateralizacao(df, n=3, tolerancia=0.005)
    #print("Lateral 3 velas: ",resultado)

    resultado2 = detectar_quebra_lateralizacao(df, n=2, tolerancia=0.005)
    #print("Lateral 2 velas: ",resultado2)
    
    tickers_STATUS[prefixo]["lateral"]= houve_quebra_lateralizacao(df, n=2, tolerancia=0.005),resultado, resultado2
    
    tickers_STATUS[prefixo]["rompeu"]=  meu_rompeu(df, 2)   #houve_quebra_lateralizacao(df, n=2, tolerancia=0.005)
    #tickers_STATUS[prefixo].get("lateral")
    
    if tickers_STATUS[prefixo].get("direcao_rsi") is None:
        tickers_STATUS[prefixo]["direcao_rsi"] = (direcao)
    else:     
        if tickers_STATUS[prefixo].get("direcao_rsi")!=direcao:
            tickers_STATUS[prefixo]["direcao_rsi"] = direcao

    # ----- 7. Exibição -----
    inverteu=tickers_STATUS[prefixo].get("inverteu", "")
    #print(f"Tipo da última vela: {tipo_vela.upper()}")
    #print(f"RSI: {[round(x,2) for x in rsi_list]}")
    #print(f"MA : {[round(x,2) for x in ma_list]}")
    #print(f"Diferenças: {[round(d,2) for d in diff_list]}")
    #print(f"Tendência da diferença: {tendencia_diff}")
    #print(f"Impulso: {impulso}")
    #print(f"ultima vela: {tipo_vela, pav_sombra ,acho, inverteu, resultado, resultado2}")
    if cruzamentos:
        print(f"Cruzamentos: {cruzamentos}")
    else:
        print("Nenhum cruzamento.")
    print(f"Direção: {direcao}")
    print(f"RecomendaçãoRSI: {recomendacao}")

    return direcao, impulso, cruzamentos, tendencia_diff, recomendacao, tipo_vela, acho, pav_sombra



"""
def intensidade_sinal_antiga(ativo, status, limiar=LIMIAR_FORCA):
    
    try:
        # book da opção
        book_opcao = mt5.market_book_get(ativo)
        compradores_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_BUY) if book_opcao else 0
        vendedores_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_SELL) if book_opcao else 0

        # ativo principal
        principal = ativo_principal(ativo)
        compradores_principal = vendedores_principal = 0
        preco_principal = None
        tick = None
        if principal:
            book_principal = mt5.market_book_get(principal)
            compradores_principal = sum(b.volume for b in book_principal if b.type == mt5.BOOK_TYPE_BUY) if book_principal else 0
            vendedores_principal = sum(b.volume for b in book_principal if b.type == mt5.BOOK_TYPE_SELL) if book_principal else 0
            tick = mt5.symbol_info_tick(principal)
            if tick:
                preco_principal = (tick.ask + tick.bid) / 2.0

        # --- ajuste conforme tipo da opção ---
        tipo_opcao = ativo[4].upper() if len(ativo) > 4 else ""

        if tipo_opcao in "ABCDEFGHIJKL":  # CALLs
            compradores = compradores_opcao + compradores_principal
            vendedores = vendedores_opcao + vendedores_principal
        elif tipo_opcao in "MNOPQRSTUVWXYZ":  # PUTs
            compradores = vendedores_opcao + compradores_principal
            vendedores = compradores_opcao + vendedores_principal
        else:
            compradores = compradores_opcao + compradores_principal
            vendedores = vendedores_opcao + vendedores_principal

        # total combinado
        total = compradores + vendedores
        if total == 0:
            return "DESCONHECIDO", 0.0, 0.0

        # proporção combinada
        if status.lower() == "compra":
            proporcao = compradores / total
            proporcao_principal = compradores_principal / (compradores_principal + vendedores_principal) if (compradores_principal + vendedores_principal) > 0 else 0
        elif status.lower() == "venda":
            proporcao = vendedores / total
            proporcao_principal = vendedores_principal / (compradores_principal + vendedores_principal) if (compradores_principal + vendedores_principal) > 0 else 0
        else:
            return "DESCONHECIDO", 0.0, 0.0

        # ajuste por spread e pressão
        if tick:
            spread = tick.ask - tick.bid
            # pressão vendedora
            if spread >= 0.02 and vendedores_principal > compradores_principal and status.lower() == "venda":
                proporcao_principal = min(1.0, proporcao_principal + 0.05)  # reforço de 5%
            # pressão compradora
            elif spread >= 0.02 and compradores_principal > vendedores_principal and status.lower() == "compra":
                proporcao_principal = min(1.0, proporcao_principal + 0.05)  # reforço de 5%

        percentual = round(proporcao * 100, 1)
        percentual_principal = round(proporcao_principal * 100, 1)
        intensidade = "FORTE" if percentual >= limiar else "FRACO"
        # reforço adicional
        ajuste = ""
        if tipo_opcao in "ABCDEFGHIJKL":  # CALLs
            if status.lower() == "compra" and preco_principal and compradores > vendedores:
                ajuste = "✔️ CALL reforçada pela alta do ativo"
            elif status.lower() == "venda" and preco_principal and vendedores > compradores:
                ajuste = "⚠️ Venda de CALL reforçada pela queda do ativo"
        elif tipo_opcao in "MNOPQRSTUVWXYZ":  # PUTs
            if status.lower() == "venda" and preco_principal and vendedores > compradores:
                ajuste = "✔️ PUT reforçada pela queda do ativo"
            elif status.lower() == "compra" and preco_principal and compradores > vendedores:
                ajuste = "⚠️ Compra de PUT reforçada pela alta do ativo"

        mensagem = (
            f"{status.upper()} {intensidade} ({percentual}%)\n"
            f"📊 Compradores: {compradores} | Vendedores: {vendedores}\n"
            f"🔗 Principal usado: {principal if principal else 'nenhum'}\n"
            f"📈 Percentual principal: {percentual_principal}%\n"
            f"{ajuste}"
        )

        return mensagem, percentual, percentual_principal

    except Exception as e:
        print(f"⚠️ MT5 book falhou para {ativo}:", e)
        return "DESCONHECIDO", 0.0, 0.0

"""
#...


# --- Funções Auxiliares ---

def _obter_volumes_book(simbolo):
    """
    Função auxiliar para extrair volumes de compra e venda do book.
    Retorna (volume_compradores, volume_vendedores).
    """
    if not simbolo:
        return 0, 0
    
    book = mt5.market_book_get(simbolo)
    if not book:
        return 0, 0

    comp = sum(b.volume for b in book if b.type == mt5.BOOK_TYPE_BUY)
    vend = sum(b.volume for b in book if b.type == mt5.BOOK_TYPE_SELL)
    return comp, vend

def _eh_put(ativo):
    """
    Verifica se o ativo é uma PUT baseado na 5ª letra (padrão B3).
    """
    if len(ativo) > 4:
        letra = ativo[4].upper()
        # M-X são as letras para PUTs
        return letra in "MNOPQRSTUVWXYZ"
    return False

# --- Função Principal ---


def intensidade_sinal(ativo, status, limiar=LIMIAR_FORCA):
    
    try:
        # book da opção
        book_opcao = mt5.market_book_get(ativo)
        compradores_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_BUY) if book_opcao else 0
        vendedores_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_SELL) if book_opcao else 0

        # ativo principal
        principal = ativo_principal(ativo)
        compradores_principal = vendedores_principal = 0
        preco_principal = None
        tick = None
        if principal:
            book_principal = mt5.market_book_get(principal)
            compradores_principal = sum(b.volume for b in book_principal if b.type == mt5.BOOK_TYPE_BUY) if book_principal else 0
            vendedores_principal = sum(b.volume for b in book_principal if b.type == mt5.BOOK_TYPE_SELL) if book_principal else 0
            tick = mt5.symbol_info_tick(principal)
            if tick:
                preco_principal = (tick.ask + tick.bid) / 2.0

        # --- identificar tipo da opção ---
        tipo_opcao = ativo[4].upper() if len(ativo) > 4 else ""

        # --- lógica combinada ---
        if tipo_opcao in "ABCDEFGHIJKL":  # CALLs
            if status.lower() == "compra":
                compradores = compradores_opcao + compradores_principal
                vendedores = vendedores_opcao + vendedores_principal
            else:  # venda de CALL
                compradores = compradores_opcao + vendedores_principal
                vendedores = vendedores_opcao + compradores_principal
        elif tipo_opcao in "MNOPQRSTUVWXYZ":  # PUTs
            if status.lower() == "compra":
                compradores = compradores_opcao + vendedores_principal
                vendedores = vendedores_opcao + compradores_principal
            else:  # venda de PUT
                compradores = compradores_opcao + compradores_principal
                vendedores = vendedores_opcao + vendedores_principal
        else:
            compradores = compradores_opcao + compradores_principal
            vendedores = vendedores_opcao + vendedores_principal

        # total combinado
        total = compradores + vendedores
        if total == 0:
            return "DESCONHECIDO", 0.0, 0.0

        # proporção combinada
        if status.lower() == "compra":
            proporcao = compradores / total
            proporcao_principal = compradores_principal / (compradores_principal + vendedores_principal) if (compradores_principal + vendedores_principal) > 0 else 0
        elif status.lower() == "venda":
            proporcao = vendedores / total
            proporcao_principal = vendedores_principal / (compradores_principal + vendedores_principal) if (compradores_principal + vendedores_principal) > 0 else 0
        else:
            return "DESCONHECIDO", 0.0, 0.0

        # ajuste por spread
        if tick:
            spread = tick.ask - tick.bid
            if spread >= 0.02:
                # Apenas ajusta se a tendência reforçar a operação
                if status.lower() == "compra" and tipo_opcao in "ABCDEFGHIJKL":  # Compra CALL
                    if compradores_principal > vendedores_principal:
                        proporcao_principal = min(1.0, proporcao_principal + 0.05)
                elif status.lower() == "venda" and tipo_opcao in "ABCDEFGHIJKL":  # Venda CALL
                    if vendedores_principal > compradores_principal:
                        proporcao_principal = min(1.0, proporcao_principal + 0.05)
                elif status.lower() == "compra" and tipo_opcao in "MNOPQRSTUVWXYZ":  # Compra PUT
                    if vendedores_principal > compradores_principal:
                        proporcao_principal = min(1.0, proporcao_principal + 0.05)
                elif status.lower() == "venda" and tipo_opcao in "MNOPQRSTUVWXYZ":  # Venda PUT
                    if compradores_principal > vendedores_principal:
                        proporcao_principal = min(1.0, proporcao_principal + 0.05)

        percentual = round(proporcao * 100, 1)
        percentual_principal = round(proporcao_principal * 100, 1)
        intensidade = "FORTE" if percentual >= limiar else "FRACO"
        
        # --- mensagens CORRIGIDAS ---
        ajuste = ""
        if tipo_opcao in "ABCDEFGHIJKL":  # CALLs
            if status.lower() == "compra" and compradores_principal > vendedores_principal:
                ajuste = "✔️ Compra de CALL alinhada com tendência de alta"
            elif status.lower() == "venda" and vendedores_principal > compradores_principal:
                ajuste = "✔️ Venda de CALL alinhada com tendência de baixa"
            elif status.lower() == "compra" and vendedores_principal > compradores_principal:
                ajuste = "⚠️ Compra de CALL contra tendência de baixa"
            elif status.lower() == "venda" and compradores_principal > vendedores_principal:
                ajuste = "⚠️ Venda de CALL contra tendência de alta"
        elif tipo_opcao in "MNOPQRSTUVWXYZ":  # PUTs
            if status.lower() == "compra" and vendedores_principal > compradores_principal:
                ajuste = "✔️ Compra de PUT alinhada com tendência de baixa"
            elif status.lower() == "venda" and compradores_principal > vendedores_principal:
                ajuste = "✔️ Venda de PUT alinhada com tendência de alta"
            elif status.lower() == "compra" and compradores_principal > vendedores_principal:
                ajuste = "⚠️ Compra de PUT contra tendência de alta"
            elif status.lower() == "venda" and vendedores_principal > compradores_principal:
                ajuste = "⚠️ Venda de PUT contra tendência de baixa"

        mensagem = (
            f"{status.upper()} {intensidade} ({percentual}%)\n"
            f"📊 Compradores: {compradores} | Vendedores: {vendedores}\n"
            f"🔗 Principal usado: {principal if principal else 'nenhum'}\n"
            f"📈 Percentual principal: {percentual_principal}%\n"
            f"{ajuste} !!"
        )

        return mensagem, percentual, percentual_principal

    except Exception as e:
        print(f"⚠️ MT5 book falhou para {ativo}:", e)
        return "DESCONHECIDO", 0.0, 0.0

"""
def intensidade_sinal(ativo, status, limiar=LIMIAR_FORCA):
    global REFORCO_PROSITIVO
    
    
    #Calcula intensidade considerando o ativo informado (opção) e o ativo principal.
    
    #Melhorias:
    #- Código mais limpo com funções auxiliares.
    #- Verificação real de variação de preço para as mensagens de reforço.
    
    try:
        # 1. Obter volumes da Opção
        compradores_opcao, vendedores_opcao = _obter_volumes_book(ativo)

        # 2. Obter dados do Ativo Principal
        principal = ativo_principal(ativo) # Assume que esta função já existe no seu código
        compradores_princ, vendedores_princ = 0, 0
        variacao_preco_principal = 0.0
        
        tick_principal = None
        
        if principal:
            # Volumes do principal
            compradores_princ, vendedores_princ = _obter_volumes_book(principal)
            
            # Dados de preço e variação do dia
            info_princ = mt5.symbol_info(principal)
            if info_princ:
                # Variação percentual do dia (necessário para a mensagem de reforço)
                if info_princ.price_change != 0:
                    variacao_preco_principal = info_princ.price_change
                
                # 🚨 AJUSTE AQUI: Calcular a Variação Percentual (utilizando price_prev)
                #if info_princ.price_prev != 0 and info_princ.price_change != 0:      
                    # Fórmula: (Variação Absoluta / Preço Anterior) * 100
                    # O resultado será, por exemplo, 1.5 para uma alta de 1.5%
                #    variacao_preco_principal = (info_princ.price_change / info_princ.price_prev) * 100
                else:
                    variacao_preco_principal = 0.0 # Define 0 se não houver preço anterior ou variação        


            # Tick para spread
            tick_principal = mt5.symbol_info_tick(principal)

        # 3. Consolidar Forças (Lógica Cruzada para PUTs)
        # Se for PUT: 
        #   Venda de PUT (Bullish) soma com Compradores do Principal.
        #   Compra de PUT (Bearish) soma com Vendedores do Principal.
        
        eh_put = _eh_put(ativo)

        if eh_put:
            # Inversão para PUTs:
            # "Compradores" aqui representa a FORÇA ALCISTA (BULLISH)
            total_compradores = vendedores_opcao + compradores_princ
            # "Vendedores" aqui representa a FORÇA BAIXISTA (BEARISH)
            total_vendedores = compradores_opcao + vendedores_princ
        else:
            # CALLs ou Ações normais (Lógica Direta)
            total_compradores = compradores_opcao + compradores_princ
            total_vendedores = vendedores_opcao + vendedores_princ

        # 4. Cálculos Percentuais
        total = total_compradores + total_vendedores
        if total == 0:
            return "DESCONHECIDO (Sem liquidez no book)", 0.0, 0.0

        proporcao_principal = 0.0
        total_princ = compradores_princ + vendedores_princ

        if status.lower() == "compra":
            proporcao = total_compradores / total
            if total_princ > 0:
                proporcao_principal = compradores_princ / total_princ
        elif status.lower() == "venda":
            proporcao = total_vendedores / total
            if total_princ > 0:
                proporcao_principal = vendedores_princ / total_princ
        else:
            return "DESCONHECIDO (Status inválido)", 0.0, 0.0

        # 5. Ajuste Fino (Spread e Pressão)
        if tick_principal:
            spread = tick_principal.ask - tick_principal.bid
            spread_relevante = 0.02 # Exemplo fixo, ideal ser % do preço
            
            # Pressão Vendedora no Principal
            if spread >= spread_relevante and vendedores_princ > compradores_princ and status.lower() == "venda":
                proporcao_principal = min(1.0, proporcao_principal + 0.05)
            
            # Pressão Compradora no Principal
            elif spread >= spread_relevante and compradores_princ > vendedores_princ and status.lower() == "compra":
                proporcao_principal = min(1.0, proporcao_principal + 0.05)

        # Formatação final
        percentual = round(proporcao * 100, 1)
        percentual_principal = round(proporcao_principal * 100, 1)
        intensidade_str = "FORTE" if percentual >= limiar else "FRACO"

        # 6. Mensagens de Reforço (Baseadas na Variação REAL do Preço)
        ajuste_msg = ""
        
                
        if not eh_put: # CALLs
    
            # === 1. REFORÇO POSITIVO: Compra (Bullish) com Ativo Subindo (Bullish) ===
            if status.lower() == "compra" and variacao_preco_principal > 0.5:
                ajuste_msg = f"✔️ Compra de CALL reforçada pela alta do ativo (+{variacao_preco_principal:.2f}%)"
                
            # === 2. ALERTA: Compra (Bullish) com Ativo Caindo (Bearish) ===
            elif status.lower() == "compra" and variacao_preco_principal < -0.5:
                ajuste_msg = f"⚠️ ALERTA: Compra de CALL contra a tendência de queda ({variacao_preco_principal:.2f}%)"
                if REFORCO_PROSITIVO: percentual=0.0
            # === 3. REFORÇO POSITIVO: Venda (Bearish) com Ativo Caindo (Bearish) ===
            elif status.lower() == "venda" and variacao_preco_principal < -0.5:
                ajuste_msg = f"✔️ Venda de CALL reforçada pela queda do ativo ({variacao_preco_principal:.2f}%)"
                
            # === 4. ALERTA: Venda (Bearish) com Ativo Subindo (Bullish) ===
            elif status.lower() == "venda" and variacao_preco_principal > 0.5:
                ajuste_msg = f"🔥 ALERTA CRÍTICO: Venda de CALL contra a forte tendência de alta (+{variacao_preco_principal:.2f}%)"
                if REFORCO_PROSITIVO: percentual=0.0
            # === 5. CENÁRIOS NEUTROS (Variação entre -0.5% e +0.5%) ===
            else:
                ajuste_msg = "🟰 Variação do Ativo Subjacente neutra (sem reforço ou alerta)."
                if REFORCO_PROSITIVO: percentual=0.0



        else: # PUTs
    
            # === CENÁRIO 1: REFORÇO POSITIVO (Se faltou no seu código) ===
            if status.lower() == "venda" and variacao_preco_principal > 0.5:
                # Vender PUT (Bullish) com ativo subindo (Bullish) = Ótimo
                ajuste_msg = f"✔️ Venda de PUT reforçada pela alta do ativo (+{variacao_preco_principal:.2f}%)"
            
            # === CENÁRIO 2: ALERTA (Presente no código original) ===
            elif status.lower() == "venda" and variacao_preco_principal < -0.5:
                # Vender PUT (Bullish) com ativo caindo (Bearish) = ALERTA
                ajuste_msg = f"⚠️ Atenção: Venda de PUT contra a tendência de queda ({variacao_preco_principal:.2f}%)"
                if REFORCO_PROSITIVO: percentual=0.0
            # === CENÁRIO 3: REFORÇO POSITIVO (Presente no código original) ===
            elif status.lower() == "compra" and variacao_preco_principal < -0.5:
                # Comprar PUT (Bearish) com ativo caindo (Bearish) = Ótimo
                ajuste_msg = f"✔️ Compra de PUT reforçada pela queda do ativo ({variacao_preco_principal:.2f}%)"
            
            # Se você quiser tratar o caso de Compra de PUT com ativo subindo (ALERTA):
            elif status.lower() == "compra" and variacao_preco_principal > 0.5:
                # Comprar PUT (Bearish) com ativo subindo (Bullish) = ALERTA
                ajuste_msg = f"⚠️ Atenção: Compra de PUT contra a tendência de alta (+{variacao_preco_principal:.2f}%)"
                if REFORCO_PROSITIVO: percentual=0.0
            else:
                ajuste_msg = "🟰 Variação do Ativo Subjacente neutra (sem reforço ou alerta)."
                if REFORCO_PROSITIVO: percentual=0.0


        # Montagem da string final
        mensagem = (
            f"{status.upper()} {intensidade_str} ({percentual}%)\n"
            f"📊 Força Bull: {total_compradores} | Força Bear: {total_vendedores}\n"
            f"🔗 Principal: {principal if principal else 'N/A'}\n"
            f"📈 Pressão Principal: {percentual_principal}%\n"
            f"{ajuste_msg}"
        )

        return mensagem, percentual, percentual_principal

    except Exception as e:
        print(f"⚠️ Erro ao calcular intensidade para {ativo}: {e}")
        # Retorna valores zerados seguros para não quebrar o fluxo
        return "ERRO NO CÁLCULO", 0.0, 0.0

"""
#..................................................................
def analise_hibrida_completa(ativo, operacao="compra"):
    # 1. Obter dados técnicos (SymbolInfo)
    symbol_info = mt5.symbol_info(ativo)
    
    if symbol_info is None:
        print(f"❌ Ativo {ativo} não encontrado!")
        return None
    
    if operacao not in ["venda", "compra"]:
        print(f"❌ Ativo {ativo} {operacao} neutro!")
        return None

    analisador_tecnico = AnalisadorTecnicoPuro()
    analise_tecnica = analisador_tecnico.analisar_ativo(symbol_info, ativo, operacao)

    # 2. Obter dados do book de ofertas
    inscricao_ok = mt5.market_book_add(ativo)
    
    if inscricao_ok:
        try:
            book_data = mt5.market_book_get(ativo)
            preco_atual_ask = symbol_info.ask

            analisador_book = AnalisadorBookOfertas()
            analise_book = analisador_book.analisar_book(book_data, preco_atual_ask, operacao)

            # ⚠️ CORREÇÃO: garantir que 'classificacao_book' exista, mesmo que vazio
            if 'classificacao_book' not in analise_book:
                analise_book['classificacao_book'] = {
                    'classificacao': 'INDEFINIDA',
                    'pontuacao_total': 5.0,
                    'desbalanceamento_atual': 1.0
                }

            # Agora sim, acessar com segurança (já garantido)
            classificacao_book = analise_book['classificacao_book']

            # Chamar a decisão híbrida passando o dicionário correto
            decisao_final = tomar_decisao_hibrida(
                analise_tecnica['decisao'],
                classificacao_book
            )
            
            return {
                'analise_tecnica': analise_tecnica,
                'analise_book': analise_book,
                'decisao_final': decisao_final,
                'operacao': operacao
            }

        finally:
            mt5.market_book_release(ativo)
    else:
        print(f"⚠️ Não foi possível acessar o book de ofertas para {ativo}")
        # Retorna apenas análise técnica (já tem a estrutura esperada)
        return analise_tecnica

def tomar_decisao_hibrida(decisao_tecnica, classificacao_book):
    """Combina análises considerando a operação."""
    
    # Garantir que classificacao_book seja um dicionário e tenha as chaves
    if not isinstance(classificacao_book, dict):
        classificacao_book = {}
    
    pontuacao_tecnica = decisao_tecnica.get('pontuacao', 5)
    pontuacao_book = classificacao_book.get('pontuacao_total', 5)
    classificacao = classificacao_book.get('classificacao', '')
    desbalanceamento = classificacao_book.get('desbalanceamento_atual', 1.0)
    
    fator_desb = 1.0 + (0.1 * (desbalanceamento - 1.0))
    
    if "RUIM PARA" in classificacao and desbalanceamento > 1.2:
        fator_desb *= 0.8
    
    pontuacao_book_ajustada = min(10, pontuacao_book * fator_desb)
    
    peso_tecnica = 0.6
    peso_book = 0.4
    if desbalanceamento > 1.8 or desbalanceamento < 0.56:
        peso_tecnica = 0.4
        peso_book = 0.6
    
    pontuacao_final = (pontuacao_tecnica * peso_tecnica) + (pontuacao_book_ajustada * peso_book)
    
    decisao = determinar_decisao(pontuacao_final, pontuacao_book_ajustada, classificacao, desbalanceamento)
    return decisao



def analisar_ambas_operacoes(ativo):
    """
    Analisa tanto compra quanto venda para o ativo e retorna a operação mais favorável.
    
    Retorna:
        dict: {
            'melhor_operacao': 'compra' ou 'venda',
            'analise_compra': resultado da análise para compra,
            'analise_venda': resultado da análise para venda,
           analisar_ambas_operacoes(ativo) 'decisao_final_melhor'  'melhor_operacao': string da decisão,
            'mensagem': texto explicativo
        }
        ou None se ambas as análises falharem.
    """
    # Mapeamento de decisões para peso (maior = mais favorável)
    peso_decisao = {
        "EXECUTAR_ORDEM": 4,
        "EXECUTAR_COM_CUIDADO": 3,
        "AGUARDAR": 2,
        "EVITAR": 1,
        None: 0
    }
    
    # Analisa compra
    analise_c = analise_hibrida_completa(ativo, "compra")
    # Analisa venda
    analise_v = analise_hibrida_completa(ativo, "venda")
    
    # Se ambas falharam (None)
    if analise_c is None and analise_v is None:
        print(f"❌ Falha na análise para {ativo} (ambos os lados)")
        return None
    
    # Função para extrair pontuação (se disponível)
    def extrair_pontuacao(analise):
        if analise is None:
            return 0
        try:
            # Tenta pegar pontuação do book
            book = analise.get('analise_book', {})
            classificacao = book.get('classificacao_book', {})
            return classificacao.get('pontuacao_total', 0)
        except:
            return 0
    
    # Função para extrair decisão e peso
    def extrair_info(analise):
        if analise is None:
            return None, 0
        decisao = analise.get('decisao_final')
        peso = peso_decisao.get(decisao, 0)
        return decisao, peso
    
    decisao_c, peso_c = extrair_info(analise_c)
    decisao_v, peso_v = extrair_info(analise_v)
    
    # Critério: primeiro compara peso da decisão, depois pontuação do book
    pont_c = extrair_pontuacao(analise_c)
    pont_v = extrair_pontuacao(analise_v)
    
    if peso_c > peso_v:
        melhor = "compra"
        melhor_analise = analise_c
    elif peso_v > peso_c:
        melhor = "venda"
        melhor_analise = analise_v
    else:
        # Empate nos pesos: desempate pela pontuação do book
        if pont_c > pont_v:
            melhor = "compra"
            melhor_analise = analise_c
        elif pont_v > pont_c:
            melhor = "venda"
            melhor_analise = analise_v
        else:
            # Empate total
            melhor = "neutro"
            melhor_analise = None
    
    # Construir mensagem explicativa
    msg = f"📊 Comparação {ativo}:\n"
    msg += f"  Compra: {decisao_c} (pontuação {pont_c:.1f})\n"
    msg += f"  Venda: {decisao_v} (pontuação {pont_v:.1f})\n"
    if melhor != "neutro":
        msg += f"  ✅ Mais favorável: {melhor.upper()}"
    else:
        msg += "  ⚖️ Ambas equivalentes"
    
    return {
        'melhor_operacao': melhor,
        'analise_compra': analise_c,
        'analise_venda': analise_v,
        'decisao_final_melhor': melhor_analise.get('decisao_final') if melhor_analise else None,
        'mensagem': msg
    }

#..................................................................
""" def analise_hibrida_completa(ativo, operacao="compra"):
    # 1. Obter dados técnicos (SymbolInfo)
    symbol_info = mt5.symbol_info(ativo)
    
    if symbol_info is None:
        print(f"❌ Ativo {ativo} não encontrado!")
        return None
    
    if operacao not in ["venda", "compra"]:
        print(f"❌ Ativo {ativo} {operacao} neutro!")
        return None

    analisador_tecnico = AnalisadorTecnicoPuro()  # Classe anterior
    analise_tecnica = analisador_tecnico.analisar_ativo(symbol_info, ativo, operacao)

    # 2. Obter dados do book de ofertas
    # IMPORTANTE: Primeiro se inscrever para receber atualizações
    inscricao_ok = mt5.market_book_add(ativo)
    
    if inscricao_ok:
        try:
            book_data = mt5.market_book_get(ativo)  # Retorna tuple de BookInfo
            preco_atual_ask = symbol_info.ask

            analisador_book = AnalisadorBookOfertas()
            # CORREÇÃO: Passar a operação para o analisador do book
            analise_book = analisador_book.analisar_book(book_data, preco_atual_ask, operacao)

            # 3. Integrar análises
            #print(f"\n📘 ANÁLISE HÍBRIDA PARA {operacao.upper()} (SymbolInfo + Book de Ofertas)")
            #print(f"   Classificação Técnica: {analise_tecnica['decisao']['decisao']}")
            #print(f"   Pontuação Técnica: {analise_tecnica['decisao']['pontuacao']:.1f}/10")
            #print(f"   Classificação do Book: {analise_book['classificacao_book']['classificacao']}")
            #print(f"   Pontuação do Book: {analise_book['classificacao_book']['pontuacao_total']:.1f}/10")

            # Tomar decisão integrada
            decisao_final = tomar_decisao_hibrida(
                analise_tecnica['decisao'],
                analise_book['classificacao_book']
            )
            #DEPOIS VOLTAR print(f"\n🎯 DECISÃO FINAL PARA {operacao.upper()}: {decisao_final}")
            
            return {
                'analise_tecnica': analise_tecnica,
                'analise_book': analise_book,
                'decisao_final': decisao_final,
                'operacao': operacao
            }

        finally:
            # Sempre cancelar a inscrição após o uso
            mt5.market_book_release(ativo)
    else:
        print(f"⚠️ Não foi possível acessar o book de ofertas para {ativo}")
        # Retorna apenas análise técnica
        print(f"\n📊 Usando apenas análise técnica para {operacao.upper()}:")
        print(f"   Classificação: {analise_tecnica['decisao']['decisao']}")
        print(f"   Pontuação: {analise_tecnica['decisao']['pontuacao']:.1f}/10")
        return analise_tecnica """
#--testar depois
""" def tomar_decisao_hibrida(decisao_tecnica, classificacao_book):
    #Combina análises considerando a operação.
    
    pontuacao_tecnica = decisao_tecnica.get('pontuacao', 5)
    pontuacao_book = classificacao_book.get('pontuacao_total', 5)
    classificacao = classificacao_book.get('classificacao', '')
    desbalanceamento = classificacao_book.get('desbalanceamento_atual', 1.0)
    
    # Fator baseado no desbalanceamento (logarítmico para suavizar)
    fator_desb = 1.0 + (0.1 * (desbalanceamento - 1.0))
    
    # Penalizar se o desbalanceamento for contra a operação
    if "RUIM PARA" in classificacao and desbalanceamento > 1.2:
        fator_desb *= 0.8
    
    pontuacao_book_ajustada = min(10, pontuacao_book * fator_desb)
    
    # Peso dinâmico baseado no desbalanceamento
    peso_tecnica = 0.6
    peso_book = 0.4
    
    # Se desbalanceamento for extremo, dar mais peso ao book
    if desbalanceamento > 1.8 or desbalanceamento < 0.56:
        peso_tecnica = 0.4
        peso_book = 0.6
    
    pontuacao_final = (pontuacao_tecnica * peso_tecnica) + (pontuacao_book_ajustada * peso_book)
    
    # Decisão considerando múltiplos fatores
    decisao = determinar_decisao(pontuacao_final, pontuacao_book_ajustada, classificacao, desbalanceamento)
    return decisao
 """
def determinar_decisao(pontuacao_final, pontuacao_book, classificacao, desbalanceamento):
    """Determina a decisão final baseada em múltiplos critérios."""
    
    criterios_positivos = 0
    criterios_negativos = 0
    
    # Critério 1: Pontuação final
    if pontuacao_final >= 7.5:
        criterios_positivos += 2
    elif pontuacao_final >= 6.0:
        criterios_positivos += 1
    elif pontuacao_final < 4.0:
        criterios_negativos += 1
    
    # Critério 2: Pontuação do book
    if pontuacao_book >= 7:
        criterios_positivos += 1
    elif pontuacao_book < 4:
        criterios_negativos += 1
    
    # Critério 3: Desbalanceamento
    if 0.8 <= desbalanceamento <= 1.25:
        criterios_positivos += 1  # Desbalanceamento moderado
    elif desbalanceamento > 2.0 or desbalanceamento < 0.5:
        criterios_negativos += 2  # Desbalanceamento extremo
    
    # Critério 4: Classificação
    if "FAVORÁVEL" in classificacao:
        criterios_positivos += 1
    elif "RUIM PARA" in classificacao:
        criterios_negativos += 1
    
    # Tomar decisão baseada no balanço de critérios
    if criterios_positivos >= 4 and criterios_negativos == 0:
        return "EXECUTAR_ORDEM"
    elif criterios_positivos >= 2 and criterios_negativos <= 1:
        return "EXECUTAR_COM_CUIDADO"
    elif criterios_negativos >= 2:
        return "BLOQUEAR"
    elif criterios_positivos == criterios_negativos:
        return "AGUARDAR"
    else:
        return "EVITAR"





def preco_medio(ativo):
    try:
        info = mt5.symbol_info_tick(ativo)
    
        if dentro_horario()and info and (info.ask is not None) and (info.bid is not None):
            return (info.ask + info.bid) / 2.0
        else: 
            return (info.bid+info.last)/2
    
    
    except Exception as e:
        print(f"⚠️ MT5 tick falhou para {ativo}:", e)
    return None


def gap_preco_real(ativo):
    try:
        info = mt5.symbol_info_tick(ativo)
        if info and (info.ask is not None) and (info.bid is not None):
            numero= abs (info.ask - info.bid)
            resultado = round(numero, 2)
            
            
            return ( resultado )
    except Exception as e:
        print(f"⚠️ MT5 tick falhou para {ativo}:", e)
    return None







def preco_real(ativo, operacao):
    try:
        info = mt5.symbol_info_tick(ativo)
        valor=0
        if info and (info.ask is not None) and (info.bid is not None):
            
            
            if operacao=="venda":
                return (info.bid)
            else :
                return (info.ask )
    except Exception as e:
        print(f"⚠️ MT5 tick falhou para {ativo}:", e)
    return None


# --- FUNÇÃO COMPARATIVA ---
def comparar_analises(ativo, status, limiar=LIMIAR_FORCA):
    """
    Executa ambas as análises e compara os resultados.
    Retorna uma análise consolidada.
    """
    print(f"🔍 ANALISANDO: {ativo} | {status.upper()}")
    print("=" * 50)
    
    # Executar ambas as análises
    resultado_antigo = intensidade_sinal_antiga(ativo, status, limiar)
    resultado_novo = intensidade_sinal(ativo, status, limiar)
    
    # Extrair dados
    msg_antiga, perc_antigo, perc_princ_antigo = resultado_antigo
    msg_nova, perc_novo, perc_princ_novo = resultado_novo
    
    # Comparação numérica
    diferenca_percentual = abs(perc_antigo - perc_novo)
    
    # Determinar concordância
    concordancia = "ALTA" if diferenca_percentual <= 10 else "MODERADA" if diferenca_percentual <= 20 else "BAIXA"
    
    # Análise de risco
    risco_antigo = "BAIXO" if perc_antigo >= limiar else "ALTO"
    risco_novo = "BLOQUEADO" if perc_novo == 0 else ("BAIXO" if perc_novo >= limiar else "ALTO")
    
    # Decisão automatizada
    decisao = ""
    if perc_novo == 0 and REFORCO_PROSITIVO:
        decisao = "🔴 BLOQUEADO - Operação contra tendência"
    elif perc_antigo >= limiar and perc_novo >= limiar:
        decisao = "✅ CONFIRMADA - Ambas análises recomendam"
    elif perc_antigo >= limiar and perc_novo < limiar and perc_novo > 0:
        decisao = "⚠️ DIVERGÊNCIA - Verificar manualmente"
    elif perc_antigo < limiar and perc_novo >= limiar:
        decisao = "🔄 NOVA ANÁLISE SUGERE ENTRADA (antiga não)"
    else:
        decisao = "⛔ EVITAR - Ambas análises não recomendam"
    
    # Exibir resultados comparativos
    print("📊 RESULTADO ANTIGO:")
    print(msg_antiga)
    print(f"\n📈 Percentual: {perc_antigo}% | Risco: {risco_antigo}")
    
    print("\n📊 RESULTADO NOVO:")
    print(msg_nova)
    print(f"\n📈 Percentual: {perc_novo}% | Risco: {risco_novo}")
    
    print("\n⚖️ COMPARAÇÃO:")
    print(f"Diferença percentual: {diferenca_percentual:.1f}%")
    print(f"Concordância: {concordancia}")
    print(f"Recomendação: {decisao}")
    print("=" * 50)
    
    # Retornar resultados consolidados
    return {
        'antigo': {
            'mensagem': msg_antiga,
            'percentual': perc_antigo,
            'risco': risco_antigo,
            'intensidade': "FORTE" if perc_antigo >= limiar else "FRACO"
        },
        'novo': {
            'mensagem': msg_nova,
            'percentual': perc_novo,
            'risco': risco_novo,
            'intensidade': "FORTE" if perc_novo >= limiar and perc_novo > 0 else "FRACO"
        },
        'comparacao': {
            'diferenca': diferenca_percentual,
            'concordancia': concordancia,
            'decisao': decisao,
            'bloqueado': perc_novo == 0 and REFORCO_PROSITIVO
        }
    }

# --- FUNÇÃO DE BATCH PARA TESTES ---
def testar_estrategias(ativos_status_lista, limiar=LIMIAR_FORCA):
    """
    Testa múltiplos ativos/status e gera relatório comparativo.
    
    Args:
        ativos_status_lista: Lista de tuplas [(ativo1, status1), (ativo2, status2), ...]
    """
    resultados = []
    estatisticas = {
        'total': 0,
        'concordantes': 0,
        'bloqueados': 0,
        'divergentes': 0,
        'melhor_antigo': 0,
        'melhor_novo': 0
    }
    
    print("🧪 INICIANDO TESTES COMPARATIVOS")
    print("=" * 60)
    
    for ativo, status in ativos_status_lista:
        estatisticas['total'] += 1
        
        print(f"\nTeste {estatisticas['total']}: {ativo} - {status}")
        
        try:
            resultado = comparar_analises(ativo, status, limiar)
            resultados.append(resultado)
            
            # Coletar estatísticas
            perc_antigo = resultado['antigo']['percentual']
            perc_novo = resultado['novo']['percentual']
            
            if resultado['comparacao']['bloqueado']:
                estatisticas['bloqueados'] += 1
            elif abs(perc_antigo - perc_novo) <= 10:
                estatisticas['concordantes'] += 1
            else:
                estatisticas['divergentes'] += 1
                
            # Qual seria melhor (considerando apenas percentual)
            if perc_antigo > perc_novo and perc_novo > 0:
                estatisticas['melhor_antigo'] += 1
            elif perc_novo > perc_antigo:
                estatisticas['melhor_novo'] += 1
                
        except Exception as e:
            print(f"❌ Erro ao testar {ativo}: {e}")
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL DE TESTES")
    print("=" * 60)
    
    if estatisticas['total'] > 0:
        print(f"Total de testes: {estatisticas['total']}")
        print(f"Concordantes (diferença ≤10%): {estatisticas['concordantes']} ({estatisticas['concordantes']/estatisticas['total']*100:.1f}%)")
        print(f"Divergentes: {estatisticas['divergentes']} ({estatisticas['divergentes']/estatisticas['total']*100:.1f}%)")
        print(f"Bloqueados (contra tendência): {estatisticas['bloqueados']} ({estatisticas['bloqueados']/estatisticas['total']*100:.1f}%)")
        print(f"Melhor análise antiga: {estatisticas['melhor_antigo']}")
        print(f"Melhor análise nova: {estatisticas['melhor_novo']}")
        
        # Sugestão baseada em estatísticas
        if estatisticas['bloqueados'] > estatisticas['total'] * 0.3:
            print("\n💡 SUGESTÃO: Nova análise está sendo muito restritiva (mais de 30% bloqueados)")
        elif estatisticas['concordantes'] > estatisticas['total'] * 0.7:
            print("\n💡 SUGESTÃO: Ambas análises concordam na maioria dos casos")
        else:
            print("\n💡 SUGESTÃO: Considere usar análise manual para casos divergentes")
    
    return resultados, estatisticas

# --- FUNÇÃO PARA ANÁLISE INDIVIDUAL DETALHADA ---
def analise_detalhada(ativo, status, limiar=LIMIAR_FORCA):
    """
    Análise detalhada com mais informações para debugging.
    """
    #print(f"🔬 ANÁLISE DETALHADA: {ativo} | {status}")
    #print("=" * 60)
    
    # Executar análises
    resultado_antigo = intensidade_sinal_antiga(ativo, status, limiar)
    resultado_novo = intensidade_sinal(ativo, status, limiar)
    
    # Extrair e mostrar dados brutos (quando disponíveis)
    try:
        # Para a análise nova, podemos obter mais dados
        book_opcao = mt5.market_book_get(ativo)
        compradores_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_BUY) if book_opcao else 0
        vendedores_opcao = sum(b.volume for b in book_opcao if b.type == mt5.BOOK_TYPE_SELL) if book_opcao else 0
        
        #print(f"\n📊 DADOS BRUTOS DO BOOK:")
        #print(f"Compradores opção: {compradores_opcao}")
        #print(f"Vendedores opção: {vendedores_opcao}")
        print(f"Razão C/V: {compradores_opcao/vendedores_opcao:.2f}" if vendedores_opcao > 0 else "Razão C/V: N/A")
        
    except Exception as e:
        print(f"⚠️ Não foi possível obter dados brutos: {e}")
    
    # Mostrar resultados
    #print("\n" + "=" * 60)
    #print("RESULTADO ANTIGO:")
    #print("-" * 30)
    #print(resultado_antigo[0])
    
    #print("\nRESULTADO NOVO:")
    #print("-" * 30)
    #print(resultado_novo[0])
    
    # Análise de trade-off
    #print("\n" + "=" * 60)
    #print("🤔 ANÁLISE DE TRADE-OFF:")
    
    antigo_forte = resultado_antigo[1] >= limiar
    novo_forte = resultado_novo[1] >= limiar and resultado_novo[1] > 0
    
    if antigo_forte and not novo_forte:
        print("⚠️ CUIDADO: Análise antiga recomenda entrada, mas nova bloqueia/rejeita")
        print("   Possíveis razões:")
        print("   1. Operação contra tendência do ativo principal")
        print("   2. Variação percentual fora dos limites aceitáveis")
        print("   3. REFORCO_PROSITIVO = True está bloqueando")
    elif not antigo_forte and novo_forte:
        print("🔄 INTERESSANTE: Nova análise vê oportunidade onde antiga não via")
        print("   Isso pode indicar:")
        print("   1. Análise de tendência identificou alinhamento favorável")
        print("   2. Pressão no book principal reforçou o sinal")
    elif antigo_forte and novo_forte:
        return("✅ CONFIRMAÇÃO FORTE: Ambas análises concordam na entrada")
    else:
        return("⛔ CONSENSO NEGATIVO: Ambas análises não recomendam entrada")
    
    return ("NEUTRO")

# Versão mínima para usar no seu código
def analise_rapida_symbolinfo(symbol_info, ativo, operacao="compra"):
    """Análise técnica rápida e independente."""
    
    analisador = AnalisadorTecnicoPuro()
    resultado = analisador.analisar_ativo(symbol_info, ativo, operacao)
    
    return {
        'decisao': resultado['decisao']['decisao'],
        'confianca': resultado['decisao']['confianca'],
        'pontuacao': resultado['decisao']['pontuacao'],
        'motivo': resultado['decisao']['motivo']
    }

# Uso:
# dados = mt5.symbol_info("VALE3")
# decisao = analise_rapida_symbolinfo(dados, "VALE3", "compra")
# if decisao['decisao'] == "EXECUTAR":
#     print("✅ Operar!")
def calcular_tamanho_posicao(confianca, capital_disponivel=10000, risco_por_trade=0.02):
    """
    Calcula o tamanho da posição baseado na confiança da análise.
    
    Args:
        confianca: Confiança da análise (0.0 a 1.0)
        capital_disponivel: Capital disponível para trading
        risco_por_trade: % do capital a arriscar por trade (padrão: 2%)
    
    Returns:
        Tamanho da posição ajustado
    """
    # Risco base ajustado pela confiança
    risco_ajustado = risco_por_trade * confianca
    
    # Valor a arriscar
    valor_arriscar = capital_disponivel * risco_ajustado
    
    # Aqui você ajustaria com base no stop loss do ativo
    # Por enquanto, retornamos um valor simbólico
    if confianca > 0.8:
        return "POSIÇÃO COMPLETA"
    elif confianca > 0.6:
        return "POSIÇÃO MÉDIA"
    elif confianca > 0.4:
        return "POSIÇÃO PEQUENA"
    else:
        return "POSIÇÃO MÍNIMA"

"""
def votar_compra_ou_vender(ativo):
    if not dentro_horario:
        return
    
    # Lista de status a serem analisados
    lista_status = ["compra", "venda"]
    
    # Obter informações do ativo uma única vez
    inform = mt5.symbol_info(ativo)
    if inform is None:
        print(f"Erro: Não foi possível obter informações para {ativo}")
        return ""
    
    # Lista de decisões que bloqueiam a operação
    lista_bloqueio = ["BLOQUEAR", "EVITAR"]
    
    # Dicionário para armazenar resultados
    resultados = {
        "compra": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0
        },
        "venda": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0
        }
    }
    
    # Analisar cada status
    for status in lista_status:
        
        # 1. Análise detalhada
        ad = analise_detalhada(ativo, status)
        
        # 2. Intensidade dos sinais
        resultado_antigo = intensidade_sinal_antiga(ativo, status)
        resultado_novo = intensidade_sinal(ativo, status)
        
        # 3. Análise completa com symbol_info
        analise_completa = analisar_com_symbolinfo(
            ativo=ativo,
            status=status,
            resultado_antigo=resultado_antigo,
            resultado_novo=resultado_novo,
            symbol_info=inform
        )
        decisao_completa = analise_completa['decisao_integrada']['decisao']
        
        
        confianca = analise_completa['decisao_integrada']['confianca']
      
        a= analise_completa['decisao_integrada'] ['detalhes'] #['direcao_tendencia']#['fatores_decisivos']
        
        b= a['direcao_tendencia']
        c= analise_completa['decisao_integrada'] ['fatores_decisivos']
        investir = calcular_tamanho_posicao(confianca, capital_disponivel=10000, risco_por_trade=0.02)

        # 4. Análise rápida
        decisao_rapida = analise_rapida_symbolinfo(inform, ativo, status)
        
        # 5. Análise do analisador principal
        resultado_analisador = analisador.analisar_ativo(
            symbol_info=inform,
            ativo=ativo,
            operacao=status
        )
        decisao_analisador = resultado_analisador['decisao']['decisao']
        
        # 6. Análise híbrida
        resultado_hibrido = analise_hibrida_completa(ativo, operacao=status)
        decisao_hibrida = resultado_hibrido['decisao_final']
        
        # Coletar todas as decisões
        todas_decisoes = [
            decisao_rapida['decisao'],
            decisao_analisador,
            decisao_completa,
            decisao_hibrida
        ]
        
        # Armazenar decisões
        resultados[status]['decisoes'] = todas_decisoes
        print (f"Aqui {b} {ativo} {status} {todas_decisoes}  {confianca}{investir} {a}  {c}")


        # Verificar se há bloqueios
        for decisao in todas_decisoes:
            if any(bloqueio in str(decisao).upper() for bloqueio in lista_bloqueio):
                resultados[status]['pode_operar'] = False
                break
        
        # Calcular score (quantas vezes aparece "EXECUTAR")
        if resultados[status]['pode_operar']:
            resultados[status]['score'] = sum(
                1 for decisao in todas_decisoes 
                if "EXECUTAR" in str(decisao).upper()
            )
    
    # Tomar decisão baseada na comparação
    if not resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        print(f"Ambas as operações em {ativo} possuem bloqueios (BLOQUEAR/EVITAR)")
        return "neutro"
    
    elif resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        print(f"Venda bloqueada, indicando COMPRA em {ativo}")
        return "compra"
    
    elif resultados["venda"]["pode_operar"] and not resultados["compra"]["pode_operar"]:
        print(f"Compra bloqueada, indicando VENDA em {ativo}")
        return "venda"
    
    # Ambos podem operar - comparar scores
    else:
        score_compra = resultados["compra"]["score"]
        score_venda = resultados["venda"]["score"]
        
        print(f"Scores: Compra={score_compra}, Venda={score_venda}")
        
        if score_compra > score_venda:
            return "compra"
        elif score_venda > score_compra:
            return "venda"
        else:
            print("Empate nos scores - nenhuma recomendação clara")
            return "neutro"
"""

#-------------------------------------------------------------------------------------------------------------
"""def votar_compra_ou_vender(ativo):
    if not dentro_horario:
        return ""
    
    # Lista de status a serem analisados
    lista_status = ["compra", "venda"]
    
    # Obter informações do ativo uma única vez
    inform = mt5.symbol_info(ativo)
    if inform is None:
        print(f"Erro: Não foi possível obter informações para {ativo}")
        return ""
    
    # Lista de decisões que bloqueiam a operação
    lista_bloqueio = ["BLOQUEAR", "EVITAR"]
    
    # Dicionário para armazenar resultados
    resultados = {
        "compra": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0
        },
        "venda": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0
        }
    }
    
    # Analisar cada status
    for status in lista_status:
        
        # 1. Análise detalhada
        ad = analise_detalhada(ativo, status)
        
        # 2. Intensidade dos sinais
        resultado_antigo = intensidade_sinal_antiga(ativo, status)
        resultado_novo = intensidade_sinal(ativo, status)
        
        # 3. Análise completa com symbol_info
        analise_completa = analisar_com_symbolinfo(
            ativo=ativo,
            status=status,
            resultado_antigo=resultado_antigo,
            resultado_novo=resultado_novo,
            symbol_info=inform
        )
        decisao_completa = analise_completa['decisao_integrada']['decisao']
        confianca = analise_completa['decisao_integrada']['confianca']
        
        # Extrair informações importantes da análise completa
        detalhes = analise_completa['decisao_integrada']['detalhes']
        direcao_tendencia = detalhes.get('direcao_tendencia', 'NEUTRA')
        tipo_opcao = detalhes.get('tipo_opcao', None)
        fatores_decisivos = analise_completa['decisao_integrada'].get('fatores_decisivos', [])
        
        # Armazenar informações
        resultados[status]['direcao_tendencia'] = direcao_tendencia
        resultados[status]['tipo_opcao'] = tipo_opcao
        resultados[status]['confianca'] = confianca
        
        # 4. Análise rápida
        decisao_rapida = analise_rapida_symbolinfo(inform, ativo, status)
        
        # 5. Análise do analisador principal
        resultado_analisador = analisador.analisar_ativo(
            symbol_info=inform,
            ativo=ativo,
            operacao=status
        )
        decisao_analisador = resultado_analisador['decisao']['decisao']
        
        # 6. Análise híbrida
        resultado_hibrido = analise_hibrida_completa(ativo, operacao=status)
        decisao_hibrida = resultado_hibrido['decisao_final']
        
        # Coletar todas as decisões
        todas_decisoes = [
            decisao_rapida['decisao'],
            decisao_analisador,
            decisao_completa,
            decisao_hibrida
        ]
        
        # Armazenar decisões
        resultados[status]['decisoes'] = todas_decisoes
        
        # Calcular bônus baseado na tendência e tipo de operação
        bonus_tendencia = calcular_bonus_tendencia(
            direcao_tendencia, 
            tipo_opcao, 
            status
        )
        resultados[status]['bonus_tendencia'] = bonus_tendencia
        
        # Verificar se há bloqueios
        for decisao in todas_decisoes:
            if any(bloqueio in str(decisao).upper() for bloqueio in lista_bloqueio):
                resultados[status]['pode_operar'] = False
                break
        
        # Calcular score base (quantas vezes aparece "EXECUTAR")
        score_base = 0
        if resultados[status]['pode_operar']:
            score_base = sum(
                1 for decisao in todas_decisoes 
                if "EXECUTAR" in str(decisao).upper()
            )
        
        # Calcular score final com bônus de tendência
        resultados[status]['score'] = score_base + bonus_tendencia
        
        # Mostrar informações de debug
        investir = calcular_tamanho_posicao(confianca, capital_disponivel=10000, risco_por_trade=0.02)
        print(f"\n📊 ANÁLISE {status.upper()} - {ativo}:")
        print(f"   Tendência: {direcao_tendencia}")
        print(f"   Tipo Opção: {tipo_opcao if tipo_opcao else 'Ação/Outro'}")
        print(f"   Score Base: {score_base}")
        print(f"   Bônus Tendência: {'+' if bonus_tendencia >= 0 else ''}{bonus_tendencia}")
        print(f"   Score Final: {resultados[status]['score']}")
        print(f"   Confiança: {confianca:.1%}")
        print(f"   Fatores: {fatores_decisivos[:2] if fatores_decisivos else 'Nenhum'}")

    # Tomar decisão baseada na comparação com consideração da tendência
    decisao_final = tomar_decisao_final_com_tendencia(resultados, ativo)
    
    return decisao_final


def calcular_bonus_tendencia(direcao_tendencia, tipo_opcao, status):
    
    #Calcula um bônus (ou penalidade) baseado no alinhamento com a tendência.
    
    #Regras:
    #- Para ações: Compra com tendência de ALTA ganha bônus
    #- Para opções PUT: Venda com tendência de ALTA ganha bônus
    #- Para opções CALL: Compra com tendência de ALTA ganha bônus
    #- Operações contra tendência sofrem penalidade
    
    
    # Se não temos tendência clara, não aplica bônus
    if direcao_tendencia == "NEUTRA":
        return 0
    
    # Para opções PUT
    if tipo_opcao == "PUT":
        if status == "compra" and direcao_tendencia == "BAIXA":
            return 2  # Bônus: Compra de PUT com tendência de baixa
        elif status == "venda" and direcao_tendencia == "ALTA":
            return 2  # Bônus: Venda de PUT com tendência de alta
        elif status == "compra" and direcao_tendencia == "ALTA":
            return -1  # Penalidade: Compra de PUT contra tendência de alta
        elif status == "venda" and direcao_tendencia == "BAIXA":
            return -1  # Penalidade: Venda de PUT contra tendência de baixa
    
    # Para opções CALL
    elif tipo_opcao == "CALL":
        if status == "compra" and direcao_tendencia == "ALTA":
            return 2  # Bônus: Compra de CALL com tendência de alta
        elif status == "venda" and direcao_tendencia == "BAIXA":
            return 2  # Bônus: Venda de CALL com tendência de baixa
        elif status == "compra" and direcao_tendencia == "BAIXA":
            return -1  # Penalidade: Compra de CALL contra tendência de baixa
        elif status == "venda" and direcao_tendencia == "ALTA":
            return -1  # Penalidade: Venda de CALL contra tendência de alta
    
    # Para ações ou outros ativos
    else:
        if status == "compra" and direcao_tendencia == "ALTA":
            return 1  # Bônus: Compra com tendência de alta
        elif status == "venda" and direcao_tendencia == "BAIXA":
            return 1  # Bônus: Venda com tendência de baixa
        elif status == "compra" and direcao_tendencia == "BAIXA":
            return -1  # Penalidade: Compra contra tendência de baixa
        elif status == "venda" and direcao_tendencia == "ALTA":
            return -1  # Penalidade: Venda contra tendência de alta
    
    return 0


def tomar_decisao_final_com_tendencia(resultados, ativo):
    
    #Toma a decisão final considerando scores e tendência.
    
    
    print(f"\n{'='*80}")
    print(f"🎯 DECISÃO FINAL PARA {ativo}")
    print(f"{'='*80}")
    
    # Caso 1: Ambas bloqueadas
    if not resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        print(f"❌ Ambas as operações possuem bloqueios (BLOQUEAR/EVITAR)")
        return "neutro"
    
    # Caso 2: Apenas compra possível
    elif resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        print(f"✅ Venda bloqueada, recomendando COMPRA")
        print(f"   Score Compra: {resultados['compra']['score']}")
        print(f"   Tendência: {resultados['compra']['direcao_tendencia']}")
        return "compra"
    
    # Caso 3: Apenas venda possível
    elif resultados["venda"]["pode_operar"] and not resultados["compra"]["pode_operar"]:
        print(f"✅ Compra bloqueada, recomendando VENDA")
        print(f"   Score Venda: {resultados['venda']['score']}")
        print(f"   Tendência: {resultados['venda']['direcao_tendencia']}")
        return "venda"
    
    # Caso 4: Ambas possíveis - comparar scores
    else:
        score_compra = resultados["compra"]["score"]
        score_venda = resultados["venda"]["score"]
        confianca_compra = resultados["compra"]["confianca"]
        confianca_venda = resultados["venda"]["confianca"]
        tendencia_compra = resultados["compra"]["direcao_tendencia"]
        tendencia_venda = resultados["venda"]["direcao_tendencia"]
        
        print(f"📊 SCORES:")
        print(f"   Compra: {score_compra} (Confiança: {confianca_compra:.1%}, Tendência: {tendencia_compra})")
        print(f"   Venda: {score_venda} (Confiança: {confianca_venda:.1%}, Tendência: {tendencia_venda})")
        
        # Diferença significativa (mais de 2 pontos)
        if abs(score_compra - score_venda) >= 2:
            if score_compra > score_venda:
                print(f"✅ Diferença significativa, recomendando COMPRA")
                return "compra"
            else:
                print(f"✅ Diferença significativa, recomendando VENDA")
                return "venda"
        
        # Diferença pequena - usar confiança como desempate
        elif score_compra > score_venda:
            print(f"✅ Pequena diferença no score, recomendando COMPRA")
            return "compra"
        elif score_venda > score_compra:
            print(f"✅ Pequena diferença no score, recomendando VENDA")
            return "venda"
        
        # Empate exato - usar confiança
        else:
            if confianca_compra > confianca_venda:
                print(f"⚖️ Empate no score, maior confiança na COMPRA")
                return "compra"
            elif confianca_venda > confianca_compra:
                print(f"⚖️ Empate no score, maior confiança na VENDA")
                return "venda"
            else:
                print(f"⚖️ Empate completo, mantendo NEUTRO")
                return "neutro"
"""
#-------------------------------------------------------------------------------------------------------------
""" def votar_compra_ou_vender(ativo, inf_unico):
    if not dentro_horario:
        return {"decisao0": "neutro", "tamanho_posicao": 0, "confianca": 0, "detalhes": {}}
    
    # Lista de status a serem analisados
    lista_status = ["compra", "venda"]
    
    # Obter informações do ativo uma única vez
    inform = inf_unico  #mt5.symbol_info(ativo)
    if inform is None:
        print(f"Erro: Não foi possível obter informações para {ativo}")
        return {"decisao1": "neutro", "tamanho_posicao": 0, "confianca": 0, "detalhes": {}}
    
    # Lista de decisões que bloqueiam a operação
    lista_bloqueio = ["BLOQUEAR", "EVITAR"]
    
    # Configurações de capital e risco
    CAPITAL_DISPONIVEL = 10000  # Pode ser uma variável global ou parâmetro
    RISCO_POR_TRADE = 0.02  # 2% do capital por trade
    
    # Dicionário para armazenar resultados
    resultados = {
        "compra": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0,
            "tamanho_posicao": 0,
            "valor_monetario": 0,
            "analise_completa": None
        },
        "venda": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0,
            "tamanho_posicao": 0,
            "valor_monetario": 0,
            "analise_completa": None
        }
    }
    
    # Analisar cada status
    for status in lista_status:
        
        # 1. Análise detalhada
        ad = analise_detalhada(ativo, status)
        
        # 2. Intensidade dos sinais
        resultado_antigo = intensidade_sinal_antiga(ativo, status)
        resultado_novo = intensidade_sinal(ativo, status)
        
        # 3. Análise completa com symbol_info
        analise_completa = analisar_com_symbolinfo(
            ativo=ativo,
            status=status,
            resultado_antigo=resultado_antigo,
            resultado_novo=resultado_novo,
            symbol_info=inform
        )
        analise_completa4 = analisar_com_symbolinfo4(
            ativo=ativo,
            status=status,
            resultado_antigo=resultado_antigo,
            resultado_novo=resultado_novo,
            symbol_info=inform
        )


        sistema = SistemaDecisaoCompleto()
        analise = sistema.analisar_operacao_completa(ativo, status, resultado_antigo, resultado_novo, inform)
        fatores_decisivos = analise.get('decisao_integrada', {}).get('fatores_decisivos', [])
        print ("@"*200,"\n",analise['analise_symbol']['recomendacao_geral'], "aqui",fatores_decisivos, status) 
        
        
#       decisao4= analise_completa4['decisao_integrada']['decisao']  
        decisao4 = analise_completa4.get('decisao_integrada', {}).get('decisao', 'ERRO')
        print("+"*30, decisao4)
        # Armazenar análise completa
        resultados[status]['analise_completa'] = analise_completa
        
        decisao_completa = analise_completa['decisao_integrada']['decisao']
        
        confianca = analise_completa.get('decisao_integrada', {}).get('confianca', 0.0)

        #confianca = analise_completa['decisao_integrada']['confianca']
        
        # Extrair informações importantes da análise completa
        #detalhes = analise_completa['decisao_integrada']['detalhes']
        detalhes = analise_completa.get('decisao_integrada', {}).get('detalhes', {})
        
        direcao_tendencia = detalhes.get('direcao_tendencia', 'NEUTRA')
        tipo_opcao = detalhes.get('tipo_opcao', None)
        fatores_decisivos = analise_completa['decisao_integrada'].get('fatores_decisivos', [])
        
        # Armazenar informações
        resultados[status]['confianca'] = confianca
        resultados[status]['direcao_tendencia'] = direcao_tendencia
        resultados[status]['tipo_opcao'] = tipo_opcao
        
        # CALCULAR TAMANHO DA POSIÇÃO BASEADO NA CONFIANÇA
        tamanho_posicao, valor_monetario = calcular_tamanho_posicao_detalhado(
            confianca=confianca,
            capital_disponivel=CAPITAL_DISPONIVEL,
            risco_por_trade=RISCO_POR_TRADE,
            ativo=ativo,
            status=status,
            direcao_tendencia=direcao_tendencia,
            tipo_opcao=tipo_opcao
        )
        
        resultados[status]['tamanho_posicao'] = tamanho_posicao
        resultados[status]['valor_monetario'] = valor_monetario
        
        # 4. Análise rápida
        decisao_rapida = analise_rapida_symbolinfo(inform, ativo, status)
        
        # 5. Análise do analisador principal
        resultado_analisador = analisador.analisar_ativo(
            symbol_info=inform,
            ativo=ativo,
            operacao=status
        )
        decisao_analisador = resultado_analisador['decisao']['decisao']
        
        # 6. Análise híbrida
        resultado_hibrido = analise_hibrida_completa(ativo, operacao=status)
        decisao_hibrida = resultado_hibrido['decisao_final']
        
        # Coletar todas as decisões
        todas_decisoes = [
            decisao_rapida['decisao'],
            decisao_analisador,
            decisao_completa,
            decisao_hibrida,
            decisao4
        ]
        
        # Armazenar decisões
        resultados[status]['decisoes'] = todas_decisoes
        
        # Calcular bônus baseado na tendência e tipo de operação
        bonus_tendencia = calcular_bonus_tendencia(
            direcao_tendencia, 
            tipo_opcao, 
            status
        )
        resultados[status]['bonus_tendencia'] = bonus_tendencia
        
        # Verificar se há bloqueios
        for decisao in todas_decisoes:
            if any(bloqueio in str(decisao).upper() for bloqueio in lista_bloqueio):
                resultados[status]['pode_operar'] = False
                break
        
        # Calcular score base (quantas vezes aparece "EXECUTAR")
        score_base = 0
        if resultados[status]['pode_operar']:
            score_base = sum(
                1 for decisao in todas_decisoes 
                if "EXECUTAR" in str(decisao).upper()
            )
        
        # Calcular score final com bônus de tendência
        resultados[status]['score'] = score_base + bonus_tendencia
        
        # Mostrar informações detalhadas
        print(f"\n📊 ANÁLISE {status.upper()} - {ativo}:")
        print(f"   Tendência: {direcao_tendencia}")
        print(f"   Tipo Opção: {tipo_opcao if tipo_opcao else 'Ação/Outro'}")
        print(f"   Score Base: {score_base}")
        print(f"   Bônus Tendência: {'+' if bonus_tendencia >= 0 else ''}{bonus_tendencia}")
        print(f"   Score Final: {resultados[status]['score']}")
        print(f"   Confiança: {confianca:.1%}")
        print(f"   Tamanho Posição: {tamanho_posicao}")
        print(f"   Valor Investido: R$ {valor_monetario:,.2f}")
        if fatores_decisivos:
            print(f"   Fatores: {', '.join(fatores_decisivos[:3])}")

    # Tomar decisão baseada na comparação com consideração da tendência
    decisao_final = tomar_decisao_final_com_tendencia(resultados, ativo)
    

    decisao_final = tomar_decisao_final_com_tendencia(resultados, ativo)
    
    # Garantir decisão válida
    if decisao_final not in ["compra", "venda", "neutro"]:
        print(f"⚠️ decisão inválida: {decisao_final}. Alterando para neutro.")
        decisao_final = "neutro"
    
    # Retorno base (sempre com detalhes)
    retorno = {
        "decisao": decisao_final,
        "tamanho_posicao": 0,
        "confianca": 0.0,
        "valor_monetario": 0.0,
        "detalhes": {
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "score": 0
        },
        "analise_completa": None
    }
    
    if decisao_final in ["compra", "venda"]:
        # Garantir que as chaves existam no resultado
        res = resultados[decisao_final]
        retorno["tamanho_posicao"] = res.get("tamanho_posicao", 0)
        retorno["confianca"] = res.get("confianca", 0.0)
        retorno["valor_monetario"] = res.get("valor_monetario", 0.0)
        retorno["detalhes"] = {
            "direcao_tendencia": res.get("direcao_tendencia", "NEUTRA"),
            "tipo_opcao": res.get("tipo_opcao", None),
            "score": res.get("score", 0)
        }
        retorno["analise_completa"] = res.get("analise_completa")
    
    return retorno
 """




""" def votar_compra_ou_vender(ativo, inf_unico):
    if not dentro_horario:
        return {"decisao0": "neutro", "tamanho_posicao": 0, "confianca": 0, "detalhes": {}}
    
    # Lista de status a serem analisados
    lista_status = ["compra", "venda"]
    
    # Obter informações do ativo uma única vez
    inform = inf_unico  # mt5.symbol_info(ativo)
    if inform is None:
        print(f"Erro: Não foi possível obter informações para {ativo}")
        return {"decisao1": "neutro", "tamanho_posicao": 0, "confianca": 0, "detalhes": {}}
    
    # Lista de decisões que bloqueiam a operação
    lista_bloqueio = ["BLOQUEAR", "EVITAR"]
    
    # Configurações de capital e risco
    CAPITAL_DISPONIVEL = 10000
    RISCO_POR_TRADE = 0.02  # 2% do capital por trade
    
    # Dicionário para armazenar resultados
    resultados = {
        "compra": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0,
            "tamanho_posicao": 0,
            "valor_monetario": 0,
            "analise_completa": None
        },
        "venda": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0,
            "tamanho_posicao": 0,
            "valor_monetario": 0,
            "analise_completa": None
        }
    }
    
    # Analisar cada status
    for status in lista_status:
        try:
            # 1. Análise detalhada
            ad = analise_detalhada(ativo, status)
            
            # 2. Intensidade dos sinais
            resultado_antigo = intensidade_sinal_antiga(ativo, status)
            resultado_novo = intensidade_sinal(ativo, status)
            
            # 3. Análise completa com symbol_info
            analise_completa = analisar_com_symbolinfo(
                ativo=ativo,
                status=status,
                resultado_antigo=resultado_antigo,
                resultado_novo=resultado_novo,
                symbol_info=inform
            )
            analise_completa4 = analisar_com_symbolinfo4(
                ativo=ativo,
                status=status,
                resultado_antigo=resultado_antigo,
                resultado_novo=resultado_novo,
                symbol_info=inform
            )

            sistema = SistemaDecisaoCompleto()
            analise = sistema.analisar_operacao_completa(ativo, status, resultado_antigo, resultado_novo, inform)
            fatores_decisivos = analise.get('decisao_integrada', {}).get('fatores_decisivos', [])
            print("@"*200, "\n", analise['analise_symbol']['recomendacao_geral'], "aqui", fatores_decisivos, status) 
            
            decisao4 = analise_completa4.get('decisao_integrada', {}).get('decisao', 'ERRO')
            print("+"*30, decisao4)
            
            # Armazenar análise completa
            resultados[status]['analise_completa'] = analise_completa
            
            decisao_completa = analise_completa['decisao_integrada']['decisao']
            
            confianca = analise_completa.get('decisao_integrada', {}).get('confianca', 0.0)
            detalhes = analise_completa.get('decisao_integrada', {}).get('detalhes', {})
            
            direcao_tendencia = detalhes.get('direcao_tendencia', 'NEUTRA')
            tipo_opcao = detalhes.get('tipo_opcao', None)
            fatores_decisivos = analise_completa['decisao_integrada'].get('fatores_decisivos', [])
            
            # Armazenar informações
            resultados[status]['confianca'] = confianca
            resultados[status]['direcao_tendencia'] = direcao_tendencia
            resultados[status]['tipo_opcao'] = tipo_opcao
            
            # CALCULAR TAMANHO DA POSIÇÃO BASEADO NA CONFIANÇA
            tamanho_posicao, valor_monetario = calcular_tamanho_posicao_detalhado(
                confianca=confianca,
                capital_disponivel=CAPITAL_DISPONIVEL,
                risco_por_trade=RISCO_POR_TRADE,
                ativo=ativo,
                status=status,
                direcao_tendencia=direcao_tendencia,
                tipo_opcao=tipo_opcao
            )
            
            resultados[status]['tamanho_posicao'] = tamanho_posicao
            resultados[status]['valor_monetario'] = valor_monetario
            
            # 4. Análise rápida
            decisao_rapida = analise_rapida_symbolinfo(inform, ativo, status)
            
            # 5. Análise do analisador principal
            resultado_analisador = analisador.analisar_ativo(
                symbol_info=inform,
                ativo=ativo,
                operacao=status
            )
            decisao_analisador = resultado_analisador['decisao']['decisao']
            
            # 6. Análise híbrida
            resultado_hibrido = analise_hibrida_completa(ativo, operacao=status)
            decisao_hibrida = resultado_hibrido['decisao_final']
            
            # Coletar todas as decisões
            todas_decisoes = [
                decisao_rapida['decisao'],
                decisao_analisador,
                decisao_completa,
                decisao_hibrida,
                decisao4
            ]
            
            # Armazenar decisões
            resultados[status]['decisoes'] = todas_decisoes
            
            # Calcular bônus baseado na tendência e tipo de operação
            bonus_tendencia = calcular_bonus_tendencia(
                direcao_tendencia, 
                tipo_opcao, 
                status
            )
            resultados[status]['bonus_tendencia'] = bonus_tendencia
            
            # Verificar se há bloqueios
            for decisao in todas_decisoes:
                if any(bloqueio in str(decisao).upper() for bloqueio in lista_bloqueio):
                    resultados[status]['pode_operar'] = False
                    break
            
            # Calcular score base (quantas vezes aparece "EXECUTAR")
            score_base = 0
            if resultados[status]['pode_operar']:
                score_base = sum(
                    1 for decisao in todas_decisoes 
                    if "EXECUTAR" in str(decisao).upper()
                )
            
            # Calcular score final com bônus de tendência
            resultados[status]['score'] = score_base + bonus_tendencia
            
            # Mostrar informações detalhadas
            print(f"\n📊 ANÁLISE {status.upper()} - {ativo}:")
            print(f"   Tendência: {direcao_tendencia}")
            print(f"   Tipo Opção: {tipo_opcao if tipo_opcao else 'Ação/Outro'}")
            print(f"   Score Base: {score_base}")
            print(f"   Bônus Tendência: {'+' if bonus_tendencia >= 0 else ''}{bonus_tendencia}")
            print(f"   Score Final: {resultados[status]['score']}")
            print(f"   Confiança: {confianca:.1%}")
            print(f"   Tamanho Posição: {tamanho_posicao}")
            print(f"   Valor Investido: R$ {valor_monetario:,.2f}")
            if fatores_decisivos:
                print(f"   Fatores: {', '.join(fatores_decisivos[:3])}")
        
        except Exception as e:
            import traceback
            print(f"\n{'='*50}")
            print(f"❌ ERRO ao processar {status.upper()} para {ativo}:")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Mensagem: {str(e)}")
            print(f"   Traceback completo:")
            traceback.print_exc()
            print(f"{'='*50}\n")
            
            # Garantir que o status tenha valores mínimos para não quebrar a decisão final
            resultados[status]['pode_operar'] = False
            resultados[status]['score'] = -999  # para que não seja escolhido
            resultados[status]['confianca'] = 0.0
            resultados[status]['direcao_tendencia'] = 'ERRO'
            resultados[status]['tipo_opcao'] = None
            resultados[status]['tamanho_posicao'] = 0
            resultados[status]['valor_monetario'] = 0.0
            resultados[status]['analise_completa'] = None
            # As demais chaves (decisoes, bonus_tendencia) já existem; mantêm-se os valores padrão iniciais

    # Tomar decisão baseada na comparação com consideração da tendência
    decisao_final = tomar_decisao_final_com_tendencia(resultados, ativo)
    
    # Garantir decisão válida
    if decisao_final not in ["compra", "venda", "neutro"]:
        print(f"⚠️ decisão inválida: {decisao_final}. Alterando para neutro.")
        decisao_final = "neutro"
    
    # Retorno base (sempre com detalhes)
    retorno = {
        "decisao": decisao_final,
        "tamanho_posicao": 0,
        "confianca": 0.0,
        "valor_monetario": 0.0,
        "detalhes": {
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "score": 0
        },
        "analise_completa": None
    }
    
    if decisao_final in ["compra", "venda"]:
        # Garantir que as chaves existam no resultado
        res = resultados[decisao_final]
        retorno["tamanho_posicao"] = res.get("tamanho_posicao", 0)
        retorno["confianca"] = res.get("confianca", 0.0)
        retorno["valor_monetario"] = res.get("valor_monetario", 0.0)
        retorno["detalhes"] = {
            "direcao_tendencia": res.get("direcao_tendencia", "NEUTRA"),
            "tipo_opcao": res.get("tipo_opcao", None),
            "score": res.get("score", 0)
        }
        retorno["analise_completa"] = res.get("analise_completa")
    
    return retorno
 """


def votar_compra_ou_vender(ativo, inf_unico):
    print(f"\n[DEBUG] Iniciando votar_compra_ou_vender para {ativo}")
    
    if not dentro_horario:
        print("[DEBUG] Fora do horário, retornando neutro")
        return {"decisao0": "neutro", "tamanho_posicao": 0, "confianca": 0, "detalhes": {}}
    
    lista_status = ["compra", "venda"]
    inform = inf_unico
    if inform is None:
        print(f"[ERRO] inform é None para {ativo}")
        return {"decisao1": "neutro", "tamanho_posicao": 0, "confianca": 0, "detalhes": {}}
    
    print(f"[DEBUG] inform obtido com sucesso para {ativo}")
    
    lista_bloqueio = ["BLOQUEAR", "EVITAR"]
    CAPITAL_DISPONIVEL = 10000
    RISCO_POR_TRADE = 0.02
    
    resultados = {
        "compra": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0,
            "tamanho_posicao": 0,
            "valor_monetario": 0,
            "analise_completa": None
        },
        "venda": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0,
            "confianca": 0,
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "bonus_tendencia": 0,
            "tamanho_posicao": 0,
            "valor_monetario": 0,
            "analise_completa": None
        }
    }
    
    for status in lista_status:
        print(f"\n[DEBUG] Processando status: {status}")
        #try:
        print(f"[DEBUG] Chamando analise_detalhada({ativo}, {status})")
        ad = analise_detalhada(ativo, status)
        
        print(f"[DEBUG] Chamando intensidade_sinal_antiga({ativo}, {status})")
        resultado_antigo = intensidade_sinal_antiga(ativo, status)
        
        print(f"[DEBUG] Chamando intensidade_sinal({ativo}, {status})")
        resultado_novo = intensidade_sinal(ativo, status)
        
        print(f"[DEBUG] Chamando analisar_com_symbolinfo({ativo}, {status})")
        analise_completa = analisar_com_symbolinfo(
            ativo=ativo,
            status=status,
            resultado_antigo=resultado_antigo,
            resultado_novo=resultado_novo,
            symbol_info=inform
        )
        print(f"[DEBUG] analise_completa recebida, tipo: {type(analise_completa)}")
        
        print(f"[DEBUG] Chamando analisar_com_symbolinfo4({ativo}, {status})")
        analise_completa4 = analisar_com_symbolinfo4(
            ativo=ativo,
            status=status,
            resultado_antigo=resultado_antigo,
            resultado_novo=resultado_novo,
            symbol_info=inform
        )
        print(f"[DEBUG] analise_completa4 recebida, tipo: {type(analise_completa4)}")
        
        print(f"[DEBUG] Instanciando SistemaDecisaoCompleto")
        sistema = SistemaDecisaoCompleto()
        analise = sistema.analisar_operacao_completa(ativo, status, resultado_antigo, resultado_novo, inform)
        fatores_decisivos = analise.get('decisao_integrada', {}).get('fatores_decisivos', [])
        print(f"[DEBUG] analise obtida, 'analise_symbol' presente? {'analise_symbol' in analise}")
        
        decisao4 = analise_completa4.get('decisao_integrada', {}).get('decisao', 'ERRO')
        print(f"[DEBUG] decisao4 = {decisao4}")
        
        resultados[status]['analise_completa'] = analise_completa
        print(f"[DEBUG] analise_completa armazenada em resultados[{status}]")
        
        print(f"[DEBUG] Acessando decisao_completa de analise_completa['decisao_integrada']['decisao']")
        decisao_completa = analise_completa['decisao_integrada']['decisao']
        print(f"[DEBUG] decisao_completa = {decisao_completa}")
        
        confianca = analise_completa.get('decisao_integrada', {}).get('confianca', 0.0)
        detalhes = analise_completa.get('decisao_integrada', {}).get('detalhes', {})
        print(f"[DEBUG] confianca = {confianca}, detalhes = {detalhes}")
        
        direcao_tendencia = detalhes.get('direcao_tendencia', 'NEUTRA')
        tipo_opcao = detalhes.get('tipo_opcao', None)
        fatores_decisivos = analise_completa['decisao_integrada'].get('fatores_decisivos', [])
        print(f"[DEBUG] direcao_tendencia = {direcao_tendencia}, tipo_opcao = {tipo_opcao}")
        
        resultados[status]['confianca'] = confianca
        resultados[status]['direcao_tendencia'] = direcao_tendencia
        resultados[status]['tipo_opcao'] = tipo_opcao
        
        print(f"[DEBUG] Chamando calcular_tamanho_posicao_detalhado")
        tamanho_posicao, valor_monetario = calcular_tamanho_posicao_detalhado(
            confianca=confianca,
            capital_disponivel=CAPITAL_DISPONIVEL,
            risco_por_trade=RISCO_POR_TRADE,
            ativo=ativo,
            status=status,
            direcao_tendencia=direcao_tendencia,
            tipo_opcao=tipo_opcao
        )
        resultados[status]['tamanho_posicao'] = tamanho_posicao
        resultados[status]['valor_monetario'] = valor_monetario
        
        print(f"[DEBUG] Chamando analise_rapida_symbolinfo")
        decisao_rapida = analise_rapida_symbolinfo(inform, ativo, status)
        
        print(f"[DEBUG] Chamando analisador.analisar_ativo")
        resultado_analisador = analisador.analisar_ativo(
            symbol_info=inform,
            ativo=ativo,
            operacao=status
        )
        decisao_analisador = resultado_analisador['decisao']['decisao']
        
        print(f"[DEBUG] Chamando analise_hibrida_completa")
        resultado_hibrido = analise_hibrida_completa(ativo, operacao=status)
        if resultado_hibrido is None:
            print(f"[ERRO] analise_hibrida_completa retornou None para {status}")
            decisao_hibrida = "ERRO_HIBRIDO"
        else:
            decisao_hibrida = resultado_hibrido.get('decisao_final', 'ERRO')
        print(f"[DEBUG] decisao_hibrida = {decisao_hibrida}")
        
        todas_decisoes = [
            decisao_rapida['decisao'],
            decisao_analisador,
            decisao_completa,
            decisao_hibrida,
            decisao4
        ]
        resultados[status]['decisoes'] = todas_decisoes
        
        bonus_tendencia = calcular_bonus_tendencia(direcao_tendencia, tipo_opcao, status)
        resultados[status]['bonus_tendencia'] = bonus_tendencia
        
        for decisao in todas_decisoes:
            if any(bloqueio in str(decisao).upper() for bloqueio in lista_bloqueio):
                resultados[status]['pode_operar'] = False
                break
        
        score_base = 0
        if resultados[status]['pode_operar']:
            score_base = sum(1 for decisao in todas_decisoes if "EXECUTAR" in str(decisao).upper())
        
        resultados[status]['score'] = score_base + bonus_tendencia
        
        print(f"\n📊 ANÁLISE {status.upper()} - {ativo}:")
        print(f"   Tendência: {direcao_tendencia}")
        print(f"   Score Final: {resultados[status]['score']}")
        print(f"   Confiança: {confianca:.1%}")
        
        """ except Exception as e:
            import traceback
            print(f"\n{'='*50}")
            print(f"❌ ERRO CAPTURADO no try para {status.upper()} - {ativo}")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Mensagem: {str(e)}")
            print(f"   Traceback completo:")
            traceback.print_exc()
            print(f"{'='*50}\n")
            
            resultados[status]['pode_operar'] = False
            resultados[status]['score'] = -999
            resultados[status]['confianca'] = 0.0
            resultados[status]['direcao_tendencia'] = 'ERRO'
            resultados[status]['tipo_opcao'] = None
            resultados[status]['tamanho_posicao'] = 0
            resultados[status]['valor_monetario'] = 0.0
            resultados[status]['analise_completa'] = None
     
    
    
    
    
    
    print(f"\n[DEBUG] Chamando tomar_decisao_final_com_tendencia")
    decisao_final = tomar_decisao_final_com_tendencia(resultados, ativo)
    print(f"[DEBUG] decisao_final retornada: {decisao_final}")
    
    if decisao_final not in ["compra", "venda", "neutro"]:
        print(f"⚠️ decisão inválida: {decisao_final}. Alterando para neutro.")
        decisao_final = "neutro"
    
    retorno = {
        "decisao": decisao_final,
        "tamanho_posicao": 0,
        "confianca": 0.0,
        "valor_monetario": 0.0,
        "detalhes": {
            "direcao_tendencia": "NEUTRA",
            "tipo_opcao": None,
            "score": 0
        },
        "analise_completa": None
    }
    
    if decisao_final in ["compra", "venda"]:
        print(f"[DEBUG] Preenchendo retorno para {decisao_final}")
        res = resultados[decisao_final]
        print(f"[DEBUG] res = {res.keys() if isinstance(res, dict) else 'não é dict'}")
        retorno["tamanho_posicao"] = res.get("tamanho_posicao", 0)
        retorno["confianca"] = res.get("confianca", 0.0)
        retorno["valor_monetario"] = res.get("valor_monetario", 0.0)
        retorno["detalhes"] = {
            "direcao_tendencia": res.get("direcao_tendencia", "NEUTRA"),
            "tipo_opcao": res.get("tipo_opcao", None),
            "score": res.get("score", 0)
        }
        retorno["analise_completa"] = res.get("analise_completa")
        print(f"[DEBUG] retorno final: {retorno}")
    else:
        print(f"[DEBUG] decisao_final neutro, retornando estrutura padrão")
    
    print(f"[DEBUG] Retornando da função votar_compra_ou_vender")
    return retorno

"""

        # ... fim do loop for ...

    # Calcular direção consolidada para uso no neutro
    direcao_consolidada = "NEUTRA"
    score_compra = resultados["compra"]["score"]
    score_venda = resultados["venda"]["score"]
    dir_compra = resultados["compra"]["direcao_tendencia"]
    dir_venda = resultados["venda"]["direcao_tendencia"]

    if dir_compra == dir_venda and dir_compra != "NEUTRA":
        direcao_consolidada = dir_compra
    else:
        if score_compra > score_venda:
            direcao_consolidada = dir_compra
        elif score_venda > score_compra:
            direcao_consolidada = dir_venda
        else:
            direcao_consolidada = dir_compra if dir_compra != "NEUTRA" else dir_venda

    # Tomar decisão baseada na comparação com consideração da tendência
    decisao_final = tomar_decisao_final_com_tendencia(resultados, ativo)
    
    if decisao_final not in ["compra", "venda", "neutro"]:
        print(f"⚠️ decisão inválida: {decisao_final}. Alterando para neutro.")
        decisao_final = "neutro"
    
    retorno = {
        "decisao": decisao_final,
        "tamanho_posicao": 0,
        "confianca": 0.0,
        "valor_monetario": 0.0,
        "detalhes": {
            "direcao_tendencia": direcao_consolidada,
            "tipo_opcao": None,
            "score": 0
        },
        "analise_completa": None
    }
    
    if decisao_final in ["compra", "venda"]:
        res = resultados[decisao_final]
        retorno["tamanho_posicao"] = res.get("tamanho_posicao", 0)
        retorno["confianca"] = res.get("confianca", 0.0)
        retorno["valor_monetario"] = res.get("valor_monetario", 0.0)
        retorno["detalhes"] = {
            "direcao_tendencia": res.get("direcao_tendencia", "NEUTRA"),
            "tipo_opcao": res.get("tipo_opcao", None),
            "score": res.get("score", 0)
        }
        retorno["analise_completa"] = res.get("analise_completa")
    else:
        # Se neutro, exibe a direção consolidada (opcional)
        print(f"📊 Decisão NEUTRA para {ativo} | Direção detectada: {direcao_consolidada}")
    
    return retorno



def votar_compra_ou_vender_antigo(ativo, inf_unico):
    if not dentro_horario:
        return
    
    # Lista de status a serem analisados
    lista_status = ["compra", "venda"]
    
    # Obter informações do ativo uma única vez
    inform = inf_unico  #mt5.symbol_info(ativo)
    if inform is None:
        print(f"Erro: Não foi possível obter informações para {ativo}")
        return ""
    
    # Lista de decisões que bloqueiam a operação
    lista_bloqueio = ["BLOQUEAR", "EVITAR"]
    
    # Dicionário para armazenar resultados
    resultados = {
        "compra": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0
        },
        "venda": {
            "decisoes": [],
            "pode_operar": True,
            "score": 0
        }
    }
    
    # Analisar cada status
    for status in lista_status:
        
        # 1. Análise detalhada
        ad = analise_detalhada(ativo, status)
        
        # 2. Intensidade dos sinais
        resultado_antigo = intensidade_sinal_antiga(ativo, status)
        resultado_novo = intensidade_sinal(ativo, status)
        
        # 3. Análise completa com symbol_info
        analise_completa = analisar_com_symbolinfo(
            ativo=ativo,
            status=status,
            resultado_antigo=resultado_antigo,
            resultado_novo=resultado_novo,
            symbol_info=inform
        )
        decisao_completa = analise_completa['decisao_integrada']['decisao']
        
        # 4. Análise rápida
        decisao_rapida = analise_rapida_symbolinfo(inform, ativo, status)
        
        # 5. Análise do analisador principal
        resultado_analisador = analisador.analisar_ativo(
            symbol_info=inform,
            ativo=ativo,
            operacao=status
        )
        decisao_analisador = resultado_analisador['decisao']['decisao']
        
        # 6. Análise híbrida
        resultado_hibrido = analise_hibrida_completa(ativo, operacao=status)
        decisao_hibrida = resultado_hibrido['decisao_final']
        
        # Coletar todas as decisões
        todas_decisoes = [
            decisao_rapida['decisao'],
            decisao_analisador,
            decisao_completa,
            decisao_hibrida
        ]
        
        # Armazenar decisões
        resultados[status]['decisoes'] = todas_decisoes
        
        # Verificar se há bloqueios
        for decisao in todas_decisoes:
            if any(bloqueio in str(decisao).upper() for bloqueio in lista_bloqueio):
                resultados[status]['pode_operar'] = False
                break
        
        # Calcular score (quantas vezes aparece "EXECUTAR")
        if resultados[status]['pode_operar']:
            resultados[status]['score'] = sum(
                1 for decisao in todas_decisoes 
                if "EXECUTAR" in str(decisao).upper()
            )
    
    # Tomar decisão baseada na comparação
    if not resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        print(f"Ambas as operações em {ativo} possuem bloqueios (BLOQUEAR/EVITAR)")
        return "neutro"
    
    elif resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        print(f"Venda bloqueada, indicando COMPRA em {ativo}")
        return "compra"
    
    elif resultados["venda"]["pode_operar"] and not resultados["compra"]["pode_operar"]:
        print(f"Compra bloqueada, indicando VENDA em {ativo}")
        return "venda"
    
    # Ambos podem operar - comparar scores
    else:
        score_compra = resultados["compra"]["score"]
        score_venda = resultados["venda"]["score"]
        
        print(f"Scores: Compra={score_compra}, Venda={score_venda}")
        
        if score_compra > score_venda:
            return "compra"
        elif score_venda > score_compra:
            return "venda"
        else:
            print("Empate nos scores - nenhuma recomendação clara")
            return "neutro"



def calcular_bonus_tendencia(direcao_tendencia, tipo_opcao, status):
    
    #Calcula um bônus (ou penalidade) baseado no alinhamento com a tendência.
    
    #Regras:
    #- Para ações: Compra com tendência de ALTA ganha bônus
    #- Para opções PUT: Venda com tendência de ALTA ganha bônus
    #- Para opções CALL: Compra com tendência de ALTA ganha bônus
    #- Operações contra tendência sofrem penalidade
    
    
    # Se não temos tendência clara, não aplica bônus
    if direcao_tendencia == "NEUTRA":
        return 0
    
    # Para opções PUT
    if tipo_opcao == "PUT":
        if status == "compra" and direcao_tendencia == "BAIXA":
            return 2  # Bônus: Compra de PUT com tendência de baixa
        elif status == "venda" and direcao_tendencia == "ALTA":
            return 2  # Bônus: Venda de PUT com tendência de alta
        elif status == "compra" and direcao_tendencia == "ALTA":
            return -1  # Penalidade: Compra de PUT contra tendência de alta
        elif status == "venda" and direcao_tendencia == "BAIXA":
            return -1  # Penalidade: Venda de PUT contra tendência de baixa
    
    # Para opções CALL
    elif tipo_opcao == "CALL":
        if status == "compra" and direcao_tendencia == "ALTA":
            return 2  # Bônus: Compra de CALL com tendência de alta
        elif status == "venda" and direcao_tendencia == "BAIXA":
            return 2  # Bônus: Venda de CALL com tendência de baixa
        elif status == "compra" and direcao_tendencia == "BAIXA":
            return -1  # Penalidade: Compra de CALL contra tendência de baixa
        elif status == "venda" and direcao_tendencia == "ALTA":
            return -1  # Penalidade: Venda de CALL contra tendência de alta
    
    # Para ações ou outros ativos
    else:
        if status == "compra" and direcao_tendencia == "ALTA":
            return 1  # Bônus: Compra com tendência de alta
        elif status == "venda" and direcao_tendencia == "BAIXA":
            return 1  # Bônus: Venda com tendência de baixa
        elif status == "compra" and direcao_tendencia == "BAIXA":
            return -1  # Penalidade: Compra contra tendência de baixa
        elif status == "venda" and direcao_tendencia == "ALTA":
            return -1  # Penalidade: Venda contra tendência de alta
    
    return 0


def calcular_tamanho_posicao_detalhado(confianca, capital_disponivel=10000, risco_por_trade=0.02, 
                                       ativo=None, status=None, direcao_tendencia="NEUTRA", 
                                       tipo_opcao=None):
    """
    Calcula o tamanho da posição baseado na confiança e outros fatores.
    
    Args:
        confianca: Confiança da análise (0.0 a 1.0)
        capital_disponivel: Capital disponível para trading
        risco_por_trade: % do capital a arriscar por trade
        ativo: Nome do ativo (para ajustes específicos)
        status: "compra" ou "venda"
        direcao_tendencia: Tendência do ativo
        tipo_opcao: Tipo da opção (CALL, PUT, None)
    
    Returns:
        tupla: (tamanho_posicao_str, valor_monetario)
    """
    
    # VALOR BASE: Capital * Risco * Confiança
    valor_base = capital_disponivel * risco_por_trade * confianca
    
    # AJUSTES BASEADOS NA CONFIANÇA
    ajuste_confianca = 1.0
    
    if confianca >= 0.9:
        ajuste_confianca = 1.5  # Máxima confiança - posição maior
        tamanho_str = "POSIÇÃO MÁXIMA"
    elif confianca >= 0.8:
        ajuste_confianca = 1.2
        tamanho_str = "POSIÇÃO ALTA"
    elif confianca >= 0.7:
        ajuste_confianca = 1.0
        tamanho_str = "POSIÇÃO COMPLETA"
    elif confianca >= 0.6:
        ajuste_confianca = 0.8
        tamanho_str = "POSIÇÃO MÉDIA"
    elif confianca >= 0.5:
        ajuste_confianca = 0.6
        tamanho_str = "POSIÇÃO MODERADA"
    elif confianca >= 0.4:
        ajuste_confianca = 0.4
        tamanho_str = "POSIÇÃO PEQUENA"
    else:
        ajuste_confianca = 0.2
        tamanho_str = "POSIÇÃO MÍNIMA"
    
    # AJUSTE POR TENDÊNCIA
    ajuste_tendencia = 1.0
    
    # Verificar se a operação está alinhada com a tendência
    if tipo_opcao == "PUT":
        if (status == "compra" and direcao_tendencia == "BAIXA") or \
           (status == "venda" and direcao_tendencia == "ALTA"):
            ajuste_tendencia = 1.3  # Alinhado com tendência - aumento 30%
        elif (status == "compra" and direcao_tendencia == "ALTA") or \
             (status == "venda" and direcao_tendencia == "BAIXA"):
            ajuste_tendencia = 0.7  # Contra tendência - redução 30%
    elif tipo_opcao == "CALL":
        if (status == "compra" and direcao_tendencia == "ALTA") or \
           (status == "venda" and direcao_tendencia == "BAIXA"):
            ajuste_tendencia = 1.3
        elif (status == "compra" and direcao_tendencia == "BAIXA") or \
             (status == "venda" and direcao_tendencia == "ALTA"):
            ajuste_tendencia = 0.7
    else:  # Ações/outros
        if (status == "compra" and direcao_tendencia == "ALTA") or \
           (status == "venda" and direcao_tendencia == "BAIXA"):
            ajuste_tendencia = 1.2
        elif (status == "compra" and direcao_tendencia == "BAIXA") or \
             (status == "venda" and direcao_tendencia == "ALTA"):
            ajuste_tendencia = 0.8
    
    # VALOR FINAL
    valor_final = valor_base * ajuste_confianca * ajuste_tendencia
    
    # LIMITES DE SEGURANÇA
    # Máximo 5% do capital em uma operação
    limite_maximo = capital_disponivel * 0.05
    valor_final = min(valor_final, limite_maximo)
    
    # Mínimo de R$ 100 para operar
    valor_final = max(valor_final, 100)
    
    # Ajustar para múltiplos de 100 (para lotes padrão)
    valor_final = round(valor_final / 100) * 100
    
    return tamanho_str, valor_final


def tomar_decisao_final_com_tendencia(resultados, ativo):
    """
    Toma a decisão final considerando scores, tendência e confiança.
    """
    
    print(f"\n{'='*80}")
    print(f"🎯 DECISÃO FINAL PARA {ativo}")
    print(f"{'='*80}")
    
    # Caso 1: Ambas bloqueadas
    if not resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        print(f"❌ Ambas as operações possuem bloqueios (BLOQUEAR/EVITAR)")
        return "neutro"
    
    # Caso 2: Apenas compra possível
    elif resultados["compra"]["pode_operar"] and not resultados["venda"]["pode_operar"]:
        confianca = resultados["compra"]["confianca"]
        valor = resultados["compra"]["valor_monetario"]
        print(f"✅ Venda bloqueada, recomendando COMPRA")
        print(f"   Score Compra: {resultados['compra']['score']}")
        print(f"   Confiança: {confianca:.1%}")
        print(f"   Valor Recomendado: R$ {valor:,.2f}")
        print(f"   Tendência: {resultados['compra']['direcao_tendencia']}")
        return "compra"
    
    # Caso 3: Apenas venda possível
    elif resultados["venda"]["pode_operar"] and not resultados["compra"]["pode_operar"]:
        confianca = resultados["venda"]["confianca"]
        valor = resultados["venda"]["valor_monetario"]
        print(f"✅ Compra bloqueada, recomendando VENDA")
        print(f"   Score Venda: {resultados['venda']['score']}")
        print(f"   Confiança: {confianca:.1%}")
        print(f"   Valor Recomendado: R$ {valor:,.2f}")
        print(f"   Tendência: {resultados['venda']['direcao_tendencia']}")
        return "venda"
    
    # Caso 4: Ambas possíveis - comparar scores
    else:
        score_compra = resultados["compra"]["score"]
        score_venda = resultados["venda"]["score"]
        confianca_compra = resultados["compra"]["confianca"]
        confianca_venda = resultados["venda"]["confianca"]
        tendencia_compra = resultados["compra"]["direcao_tendencia"]
        tendencia_venda = resultados["venda"]["direcao_tendencia"]
        valor_compra = resultados["compra"]["valor_monetario"]
        valor_venda = resultados["venda"]["valor_monetario"]
        
        print(f"📊 COMPARAÇÃO DETALHADA:")
        print(f"   COMPRA:")
        print(f"     • Score: {score_compra}")
        print(f"     • Confiança: {confianca_compra:.1%}")
        print(f"     • Valor: R$ {valor_compra:,.2f}")
        print(f"     • Tendência: {tendencia_compra}")
        
        print(f"\n   VENDA:")
        print(f"     • Score: {score_venda}")
        print(f"     • Confiança: {confianca_venda:.1%}")
        print(f"     • Valor: R$ {valor_venda:,.2f}")
        print(f"     • Tendência: {tendencia_venda}")
        
        # Critérios de decisão (ponderados)
        peso_score = 0.4
        peso_confianca = 0.4
        peso_tendencia = 0.2
        
        # Normalizar scores para 0-1
        score_total = score_compra + score_venda
        if score_total > 0:
            score_norm_compra = score_compra / score_total
            score_norm_venda = score_venda / score_total
        else:
            score_norm_compra = score_norm_venda = 0.5
        
        # Pontuação ponderada
        pontuacao_compra = (
            (score_norm_compra * peso_score) +
            (confianca_compra * peso_confianca) +
            (1.0 if tendencia_compra == "ALTA" else 0.5 if tendencia_compra == "NEUTRA" else 0.0) * peso_tendencia
        )
        
        pontuacao_venda = (
            (score_norm_venda * peso_score) +
            (confianca_venda * peso_confianca) +
            (1.0 if tendencia_venda == "BAIXA" else 0.5 if tendencia_venda == "NEUTRA" else 0.0) * peso_tendencia
        )
        
        print(f"\n📈 PONTUAÇÃO PONDERADA:")
        print(f"   Compra: {pontuacao_compra:.3f}")
        print(f"   Venda: {pontuacao_venda:.3f}")
        
        # Tomar decisão
        diferenca = abs(pontuacao_compra - pontuacao_venda)
        
        if pontuacao_compra > pontuacao_venda:
            if diferenca > 0.1:  # Diferença significativa
                print(f"✅ Diferença significativa, recomendando COMPRA")
            else:
                print(f"✅ Pequena vantagem, recomendando COMPRA")
            return "compra"
        elif pontuacao_venda > pontuacao_compra:
            if diferenca > 0.1:
                print(f"✅ Diferença significativa, recomendando VENDA")
            else:
                print(f"✅ Pequena vantagem, recomendando VENDA")
            return "venda"
        else:
            # Empate exato - usar confiança como critério final
            if confianca_compra > confianca_venda:
                print(f"⚖️ Empate, maior confiança na COMPRA")
                return "compra"
            elif confianca_venda > confianca_compra:
                print(f"⚖️ Empate, maior confiança na VENDA")
                return "venda"
            else:
                print(f"⚖️ Empate completo, mantendo NEUTRO")
                return "neutro"


# Função para executar a ordem com o tamanho correto
def executar_ordem_com_tamanho_ajustado(ativo, operacao, resultado_analise):
    """
    Executa uma ordem com o tamanho ajustado baseado na análise.
    
    Args:
        ativo: Nome do ativo
        operacao: "compra" ou "venda"
        resultado_analise: Resultado da função votar_compra_ou_vender
    """
    
    if resultado_analise["decisao"] == "neutro":
        print(f"❌ Nenhuma operação recomendada para {ativo}")
        return False
    
    if resultado_analise["decisao"] != operacao:
        print(f"❌ Operação {operacao} não está alinhada com recomendação {resultado_analise['decisao']}")
        return False
    
    confianca = resultado_analise["confianca"]
    tamanho_posicao = resultado_analise["tamanho_posicao"]
    valor_investir = resultado_analise["valor_monetario"]
    
    print(f"\n🚀 EXECUTANDO ORDEM:")
    print(f"   Ativo: {ativo}")
    print(f"   Operação: {operacao.upper()}")
    print(f"   Confiança: {confianca:.1%}")
    print(f"   Tamanho Posição: {tamanho_posicao}")
    print(f"   Valor a Investir: R$ {valor_investir:,.2f}")
    
    # Aqui você colocaria sua lógica de execução de ordem na corretora
    # Exemplo:
    # lotes = calcular_lotes_por_valor(valor_investir, ativo)
    # ordem = {
    #     "symbol": ativo,
    #     "action": mt5.TRADE_ACTION_DEAL,
    #     "type": mt5.ORDER_TYPE_BUY if operacao == "compra" else mt5.ORDER_TYPE_SELL,
    #     "volume": lotes,
    #     "price": mt5.symbol_info_tick(ativo).ask if operacao == "compra" else mt5.symbol_info_tick(ativo).bid,
    #     "deviation": 10,
    #     "magic": 234000,
    #     "comment": f"AutoTrade Conf:{confianca:.1%}",
    #     "type_time": mt5.ORDER_TIME_GTC,
    #     "type_filling": mt5.ORDER_FILLING_IOC,
    # }
    # 
    # resultado = mt5.order_send(ordem)
    
    # Por enquanto, apenas simulando
    print(f"   [SIMULAÇÃO] Ordem de {operacao} para {ativo} no valor de R$ {valor_investir:,.2f}")
    
    # Salvar registro da operação
    salvar_registro_operacao(ativo, operacao, confianca, valor_investir, resultado_analise)
    
    return True


def enviar_ordem(ticker, tipo, quantidade, abre):
    """
    tipo: 'buy' ou 'sell'
    quantidade: número de ações (lotes * 100 se necessário)
    """
    tipo_o="buy" if tipo=="compra" else ("sell" if tipo=="venda" else "") 
    
    dados = {
        "ticker": ticker,
        "acao": tipo_o,
        "quantidade": quantidade,
        "abre": abre
    }
    with open(ORDEM_PATH, "w") as f:
        json.dump(dados, f)
    print(f"Ordem salva: {dados}")



def salvar_registro_operacao(ativo, operacao, confianca, valor, resultado_analise):
    """Salva o registro da operação para análise posterior."""
    
    registro = {
        "timestamp": datetime.datetime.now().isoformat(),
        "ativo": ativo,
        "operacao": operacao,
        "confianca": confianca,
        "valor_investido": valor,
        "tendencia": resultado_analise["detalhes"].get("direcao_tendencia", "NEUTRA"),
        "tipo_opcao": resultado_analise["detalhes"].get("tipo_opcao", None),
        "score": resultado_analise["detalhes"].get("score", 0)
    }
    
    # Aqui você salvaria em um arquivo ou banco de dados
    # Exemplo: salvar_em_json("registro_operacoes.json", registro)
    
    print(f"📝 Registro salvo: {registro}")
#-------------------------------------------------------------------------------------------------------------


# --- Processa comandos ---
async def processar_comando(msg_text, chat_id):
    global ATIVOS, OBSERVAR, MINI_STOP_GAIN_PADRAO, STOP_LOSS_PADRAO, tickers_STATUS
    # Definição dos filtros com índice
    FILTROS = {
    1: "MOSTRAR_MSGS",
    2: "MOSTRAR_FOTOS",
    3: "MOSTRAR_PYTHON",
    4: "FILTRAR_MENSAGEM",
    5: "APENAS_MSGS_STOP"
}
    
    
    try:
        msg_text = msg_text.strip()

        if msg_text.startswith("/op"):
            partes = msg_text.split()
            if len(partes) >= 5:
                ativo   = partes[1].upper()
                qtd     = float(partes[2])
                entrada = float(partes[3])
                tipo    = partes[4].lower()
                
                
                stop_loss_pct = float(partes[5]) if len(partes) >= 6 else STOP_LOSS_PADRAO
                mini_stop_pct = float(partes[6]) if len(partes) >= 7 else MINI_STOP_GAIN_PADRAO
                # calcula valor de stop loss
                mensagem_intensidade, percentual, perc_principal = intensidade_sinal(ativo, tipo)

                if tipo == "compra":
                    stop_loss_valor = entrada * (1 - stop_loss_pct/100.0)
                else:  # venda
                    stop_loss_valor = entrada * (1 + stop_loss_pct/100.0)


                ATIVOS[ativo] = {"qtd": qtd, "entrada": entrada, "tipo": tipo, "stop_loss_pct": stop_loss_pct,
                    "stop_loss_valor": stop_loss_valor,
                                 "ultimo_status": None, "max_diff": 0.0,
                    "mini_stop_pct": mini_stop_pct, "mute": False , "intensidade":percentual, "historico": "humano"  }
                salvar_ativos()
                enviar_ordem(ativo, tipo, qtd, "1")


                await enviar_telegram(f"✅ {tipo.capitalize()} registrada: {ativo} | Entrada: {entrada:.2f} | Qtd: {qtd} \n{mensagem_intensidade}", "", chat_id)

        elif msg_text.startswith("/mini"):
            partes = msg_text.split()
            if len(partes) >= 3:
                ativo = partes[1].upper()
                mini_stop_pct = float(partes[2])
                if ativo in ATIVOS:
                    ATIVOS[ativo]["mini_stop_pct"] = mini_stop_pct
                    salvar_ativos()
                    await enviar_telegram(
                        f"⚙️ Mini Stop atualizado para {ativo}: {mini_stop_pct:.1f}% abaixo do lucro máximo",
                        "",
                        chat_id
                    )
                else:
                    await enviar_telegram(f"❌ Ativo {ativo} não encontrado.", "", chat_id)

        elif msg_text.startswith("/fim"):
            partes = msg_text.split()
            if len(partes) >= 3:
                ativo = partes[1].upper()
                valor_final = float(partes[2])

                if ativo in ATIVOS:
                    """dados = ATIVOS[ativo]
                    qtd = dados.get("qtd", 1.0)
                    tipo = dados.get("tipo", "compra")
                    entrada = dados.get("entrada", 0.0)
                    mini_stop_pct = dados.get("mini_stop_pct", 30.0)
                    

                    diff_unit = valor_final - entrada if tipo == "compra" else entrada - valor_final
                    resultado_final = diff_unit * qtd

                    resposta = (f"✅ Operação ENCERRADA: {ativo}\n"
                                f"Entrada: {entrada:.2f} | Final: {valor_final:.2f} | Qtd: {qtd}\n"
                                f"Tipo: {tipo} | Resultado Final: {resultado_final:.2f}")"""
                    
                    resposta = finalizar_ativo(ativo, valor_final  )
                    
                    await enviar_telegram(resposta, "", chat_id)

                    #FINALIZADOS[ativo] = {"qtd": qtd, "entrada": entrada, "tipo": tipo, "r_fim":resultado_final ,"mini_stop_pct": mini_stop_pct}
                    #salvar_finalizados()    
                    #del OBSERVAR[ativo]
                    #del ATIVOS[ativo]                    
                    #salvar_ativos()
                
                if len(partes)==4 and (partes[3]== "ver"):
                    ativo = partes[1].upper()
                    preco_ini = valor_final
                    if preco_ini:
                        OBSERVAR[ativo] = {
                            "preco_inicial": preco_ini,
                            "status": "indefinido",
                            "ultimo_diff": 0.0
                        }
                        await enviar_telegram(f"👀 Observando {ativo} | Preço inicial: {preco_ini:.2f}", "", chat_id)
                    else:
                        await enviar_telegram(f"❗ Não foi possível obter preço de {ativo}", "", chat_id)

                    

        elif msg_text.startswith("/hull"):
            partes = msg_text.split()
            if len(partes) >= 2:
                prefixo = partes[1].upper()[:4]
                if prefixo not in tickers_STATUS:
                    tickers_STATUS[prefixo] = {}
                    tickers_STATUS[prefixo]["micro_tende"] = partes[2].upper()

        elif msg_text.startswith("/ver"):
            partes = msg_text.split()
            if len(partes) >= 2:
                ativo = partes[1].upper()
                preco_ini = preco_medio(ativo)
                prc= preco_real(ativo, "compra")
                prv= preco_real(ativo, "venda")
                prx=prc*prv
    

                if preco_ini>0.0 and prx>0.0:
                    
                    #analisar o cenario de compra e venda se estiver ok ja operar direto
                    
                    OBSERVAR[ativo] = {
                        "preco_inicial": preco_ini,
                        "status": "indefinido",
                        "ultimo_diff": 0.0,
                        "reset":0, "intensidade":0.0
                        
                    }
                    await enviar_telegram(f"👀 Observando {ativo} | Preço inicial: {preco_ini:.2f}", "", chat_id)
                else:
                    await enviar_telegram(f"❗ Não foi possível obter preço de {ativo}", "", chat_id)
        elif msg_text.startswith("/ana"):
            partes = msg_text.split()
            
            if len(partes) >= 2:
                ativo = partes[1].upper()
                preco_ini = preco_medio(ativo)
                if preco_ini:
                    
                    """inform = mt5.symbol_info(ativo)
                    decisaoA_R_venda = analise_rapida_symbolinfo(inform, ativo, "venda")
                    decisaoA_R_compra = analise_rapida_symbolinfo(inform, ativo, "compra")
                    
                    
                    decisaoA_H_venda  = analise_hibrida_completa(ativo, operacao="venda")
                    decisaoA_H_compra  = analise_hibrida_completa(ativo, operacao="compra")"""
                    v_c_v= votar_compra_ou_vender_antigo(ativo)
                    decisaoA_H_venda  = analise_hibrida_completa(ativo, operacao="venda")
                    print ("aqui a decisao", decisaoA_H_venda['decisao_final'],"/", decisaoA_H_venda['analise_book']['classificacao_book']['classificacao'])  #'recomendacao'
                    
                    
                    """print( f"Hibrido venda: {  decisaoA_H_venda['decisao_final']  } |compra: {decisaoA_H_compra['decisao_final']}" )
                    
                    print( f"Rapido venda: {decisaoA_R_venda['decisao']} |compra: {decisaoA_R_compra['decisao']}" )
                    """
                            
                   
                    
                    await enviar_telegram(f"👀 Observando {ativo} | Preço inicial: {preco_ini:.2f} | {v_c_v} ", "", chat_id)
                else:
                    await enviar_telegram(f"❗ Não foi possível obter preço de {ativo}", "", chat_id)    


        elif msg_text == "/stats_ia":
            """Mostra estatísticas da rede neural"""
            try:
                stats = rede.get_estatisticas()
                #fab
                
                if stats and stats.get('total_operacoes', 0) > 0:
                    mensagem = (
                        f"🧠 **ESTATÍSTICAS DA IA**\n"
                        f"{'='*30}\n"
                        f"📊 Total de operações: {stats.get('total_operacoes', 0)}\n"
                        f"🎯 Taxa de acerto: {stats.get('taxa_acerto', 0):.1f}%\n"
                        f"💰 Lucro médio: {stats.get('lucro_medio', 0):.2f}%\n"
                        f"📈 Lucro total: {stats.get('lucro_total', 0):.2f}\n"
                        f"📈 Maior lucro: {stats.get('maior_lucro', 0):.2f}\n"
                        f"📉 Maior prejuízo: {stats.get('maior_prejuizo', 0):.2f}\n"
                        f"📊 Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}\n"
                        f"{'='*30}\n"
                        f"📊 Pesos do ensemble:\n"
                        f"   🌲 Random Forest: {rede.ensemble.pesos_ensemble.get('random_forest', 0)*100:.1f}%\n"
                        f"   📈 Gradient Boosting: {rede.ensemble.pesos_ensemble.get('gradient_boosting', 0)*100:.1f}%\n"
                        f"   ⚡ XGBoost: {rede.ensemble.pesos_ensemble.get('xgboost', 0)*100:.1f}%\n"
                        f"   🧠 LSTM: {rede.ensemble.pesos_ensemble.get('lstm', 0)*100:.1f}%"
                    )
                else:
                    mensagem = "⚠️ Ainda não há operações suficientes para estatísticas (mínimo 1)"
                
                await enviar_telegram(mensagem, "", chat_id)
                
            except Exception as e:
                await enviar_telegram(f"❌ Erro ao obter estatísticas: {str(e)}", "", chat_id)    


        
        elif msg_text == "/status":
            if not ATIVOS:
                await enviar_telegram("Nenhum ativo registrado.", "", chat_id)
            else:
                resumo = "📊 Status atual dos ativos:\n"
                total_ganho = 0.0
                for ativo, dados in list(ATIVOS.items()):

                    preco = preco_medio(ativo)
                    if preco:
                        entrada = dados["entrada"]
                        tipo    = dados["tipo"]
                        qtd     = dados.get("qtd", 1.0)

                        diff_unit = preco - entrada if tipo == "compra" else entrada - preco
                        diff = diff_unit * qtd

                        dados["max_diff"] = max(dados.get("max_diff", 0.0), diff)
                        dados["ultimo_status"] = diff

                        max_diff = dados["max_diff"]
                        status   = "positivo" if diff > 0 else "negativo"

                        total_ganho += diff

                        stop_loss_valor = dados["stop_loss_valor"]
                        stop_loss_pct   = dados["stop_loss_pct"]

                        mini_stop_pct = dados.get("mini_stop_pct", 30.0)
                        mini_stop_valor = max_diff * (1 - mini_stop_pct/100.0) if max_diff > 0 else 0.0

                        resumo += (
                            f"\n-----------------------------------\n{ativo} | Entrada:{entrada:.2f} | Atual:{preco:.2f} | Qtd:{qtd} | Tipo:{tipo}\n"
                            f"   ➡️ Status:{status} | Ganho atual:{diff:.2f} | Máx ganho:{max_diff:.2f}\n"
                            f"   📅 Stop Loss:{stop_loss_valor:.2f} ({stop_loss_pct:.1f}%) | "
                            f"Mini Stop:{mini_stop_valor:.2f} ({mini_stop_pct:.1f}% abaixo do máximo)\n"
                        )

                resumo += f"\n💰 Ganho Total: {total_ganho:.2f}"
                await enviar_telegram(resumo, "", chat_id)

        #elif msg_text == "/filtros":
        #    await enviar_telegram(f"MOSTRAR_MSGS = {MOSTRAR_MSGS} \n MOSTRAR_FOTOS = {MOSTRAR_FOTOS} \n MOSTRAR_PYTHON = {MOSTRAR_PYTHON} \n FILTRAR_MENSAGEM = {FILTRAR_MENSAGEM}", "", chat_id)


        
        elif msg_text == "/help":
            await enviar_telegram(
                "📋 Comandos disponíveis:\n"
                "/op <ativo> <qtd> <preço_ini> <compra/venda> [stop_loss_pct] [mini_stop_pct]\n"
                "   ➡️ Registra operação. Se não informar, usa Stop Loss=5% e Mini Stop=30%\n\n"
                "/fim <ativo> <valor_final>\n"
                "   ➡️ Encerra operação e mostra resultado final\n\n"
                "/ver <ativo>\n"
                "   ➡️ Observa ativo sem registrar operação\n\n"
                "/status\n"
                "   ➡️ Mostra status atual dos ativos, incluindo Stop Loss e Mini Stop\n\n"
                "/mini <ativo> <percentual>\n"
                "   ➡️ Atualiza Mini Stop de um ativo já registrado\n\n"
                "/filtros\n"
                "   ➡️ Mostra filtros atuais da GUI\n\n"
                "/filtro NOME = 0 ou 1\n"
                "   ➡️ Atualiza filtros (MOSTRAR_MSGS, MOSTRAR_FOTOS, MOSTRAR_PYTHON, FILTRAR_MENSAGEM)\n\n"
                "/help\n"
                "   ➡️ Mostra esta lista de comandos",
                "",
                chat_id
            )
        
        elif msg_text == "/filtros":
            filtros = (
                f"📋 Filtros atuais:\n"
                f"-0 SOMENTE STOPS: {'✅ Ativo' if APENAS_MSGS_STOP else '❌ Inativo'}\n"
                f"-1 Mensagens recebidas: {'✅ Ativo' if MOSTRAR_MSGS else '❌ Inativo'}\n"
                f"-2 Fotos recebidas: {'✅ Ativo' if MOSTRAR_FOTOS else '❌ Inativo'}\n"
                f"-3 Mensagens Python: {'✅ Ativo' if MOSTRAR_PYTHON else '❌ Inativo'}\n"
                f"-4 Filtrar mensagens: {'✅ Ativo' if FILTRAR_MENSAGEM else '❌ Inativo'}"
            )
            await enviar_telegram(filtros, "", chat_id)

        elif msg_text.startswith("/filtro"):
            try:
                # Exemplo: "/filtro MOSTRAR_MSGS = 0"
                partes = msg_text.replace("=", " ").split()
                if len(partes) >= 3:
                    int_var_nome = int( partes[1].strip())
                    
                    valor = int(partes[2].strip())
                    nome_filtro= ["APENAS_MSGS_STOP","MOSTRAR_MSGS", "MOSTRAR_FOTOS", "MOSTRAR_PYTHON", "FILTRAR_MENSAGEM"]
                    
                    
                    
                    #var_nome= nome_filtro[int_var_nome]
                    if 0 <= int_var_nome < len(nome_filtro):
                        var_nome = nome_filtro[int_var_nome]
                        globals()[var_nome] = bool(valor)
                        

                        await enviar_telegram(
                            f"⚙️ Filtro atualizado:\n{int_var_nome} - {var_nome} = {'Ativo ✅' if globals()[var_nome] else 'Inativo ❌'}",
                            "",chat_id)
                    
                    else:
                        await enviar_telegram(f"❌ Filtro '{var_nome}' não reconhecido.", "", chat_id)
                else:
                    await enviar_telegram("❌ Formato inválido. Use: /filtro NOME = 0 ou 1", "", chat_id)
            except Exception as e:
                print("⚠️ Erro ao processar comando /filtro:", e)
    except Exception as e:
        print("⚠️ Erro ao processar comando:", e)


# --- Checa mensagens ---
async def checar_mensagens():
    last_update_id = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                response = await client.post(BASE_URL + "getUpdates", json={"offset": last_update_id + 1, "timeout": 25})
                updates = response.json()

                for update in updates.get("result", []):
                    last_update_id = update.get("update_id", last_update_id)
                    message = update.get("channel_post") or update.get("message")
                    if message and "text" in message:
                        msg_text = message["text"].strip()
                        chat_id = message["chat"]["id"]
                        await processar_comando(msg_text, chat_id)

            except Exception as e:
                print("⚠️ Erro ao checar mensagens:", repr(e))

            await asyncio.sleep(2)


# --- Monitoramento ---
async def monitorar_ativos():
   #global ALERTA_ATUAL,NOVA_MSG,INTENSAO,LIMIAR_PERDA,tickers_STATUS,VL_HUMANO_ZERADO,SENSIBILIDADE_ENTRADA ,STOP_LOSS_PADRAO,STOP_LOSS_PADRAO_POSITIVO, ultimo_positivo5,ESTRATEGIAS_ruins, ATIVO_COM_ALERTA,PREJUIZO_MAX_ZERADO ,MINI_STOP_GAIN_PADRAO,QTD_AUTO ,GATILHO_DIFF_PRECO, IDENTIFICADOR_ROBO, ROBO_AR, ROBO_AA, ROBO_AC, ROBO_HR, REGRA2CENTS
   
    global ALERTA_ATUAL, NOVA_MSG,UMA_OPCAO_P_LETRA_por_ROBO, INTENSAO, LIMIAR_PERDA,DISTANCIA_TRAILING ,tickers_STATUS, VL_HUMANO_ZERADO, SENSIBILIDADE_ENTRADA, STOP_LOSS_PADRAO, STOP_LOSS_PADRAO_POSITIVO, ultimo_positivo5, ESTRATEGIAS_ruins, ATIVO_COM_ALERTA, PREJUIZO_MAX_ZERADO, MINI_STOP_GAIN_PADRAO, QTD_AUTO, GATILHO_DIFF_PRECO, IDENTIFICADOR_ROBO, ROBO_AR, ROBO_AA, ROBO_AC, ROBO_HR, REGRA2CENTS
   
    while True:
        try:
            # ativos registrados

            #se lucro ou prejuio TESTAR FECHAR OPERACAO E LV  E FRCHAR OPERACAO T^ PARA SAIR   EM SITUAÇÕES DE REVERSAO    EXEMPLO VENDA DE CALL FECHAR OPERACAO E T^ OU COMPRA DE CALL FECHAR OPERACAO E LV 
            # Conjunto com todos os códigos (opções) que estão sendo observados ou em posição
            todos_ativos = set(OBSERVAR.keys()) | set(ATIVOS.keys())
            # Extrai o principal de cada um e guarda em um conjunto (já elimina duplicatas)
            principais_unicos = {ativo_principal(ativo) for ativo in todos_ativos}

            # Se quiser uma lista ordenada, faça:
            lista_principais = sorted(principais_unicos)
            sinal2=";)"
            for principais in lista_principais:
                resultado = sinal_opcoes_30min_melhorado(principais)
                sinal2 = resultado.get('sinal', '')
                



            for ativo, dados in list(ATIVOS.items()):

                preco = preco_medio(ativo)
                
                # depois testar aqui quanto tempo leva da mudanca para o pratico   rompimento_saida(ativo, 1, timeframe=5)
                # rompe= rompimento_saida(ativo, 1, timeframe=5)
                # rompeu=rompe[0]
                # direcao_rompe=rompe[1]
                
                if preco:
                    entrada = dados["entrada"]
                    tipo    = dados["tipo"]
                    qtd     = dados.get("qtd", 1.0)
                    
                    stop_loss_valor = dados["stop_loss_valor"]
                    stop_loss_pct = dados["stop_loss_pct"]
                    diff_unit = preco - entrada if tipo == "compra" else entrada - preco
                    diff = diff_unit * qtd
                    status = "positivo" if diff > 0 else "negativo"
                    mini_stop_pct = dados.get("mini_stop_pct", 30.0)
                    infoATIVOS = tickers_STATUS.get(ativo.upper()[:4], {})
                    
                   
                    ddrsi= determinar_direcao_RSI(ativo,3)  
                    
                            
                    impulso=ddrsi[1]#('impulso')                       
                    pavio=ddrsi[7]#('pav_sombra')
                    resultado_romp_saida = rompimento_saida(ativo, n=1, timeframe=2)
                    rompeu5 = resultado_romp_saida[0]
                    positivo5 = resultado_romp_saida[1]
                    msg_panico5 = resultado_romp_saida[2]
                    sentido_posi5=resultado_romp_saida[3]

                    print (f"{ativo} -- {impulso }")  # para saida 



                        
    
                    # ========== INÍCIO do monitoramento de velocidade de perda ==========
                    now =   datetime.datetime.now() # datetime.now()
                    if ativo in ultimo_diff:
                        diff_anterior, ts_anterior = ultimo_diff[ativo]
                        if diff != diff_anterior:   # só registra se houve mudança
                            delta_diff = diff - diff_anterior
                            delta_tempo = (now - ts_anterior).total_seconds()
                            if delta_tempo > 0:
                                velocidade_perda = delta_diff / delta_tempo   # R$/segundo
                                # Exibe ou armazena a velocidade (ex: para perda > X)
                                if velocidade_perda < - LIMIAR_PERDA:   # ajuste o limiar negativo conforme necessário
                                    
                                    msg_v=(f"⚠️ Perda acelerada em {ativo}: \n {velocidade_perda:.3f} R$/segundo \n (diff mudou de {diff_anterior:.2f} para {diff:.2f})")
                                    print(msg_v)
                                    await enviar_telegram(msg_v)
                            # Atualiza o registro
                                # elif velocidade_perda < -0.02:   # perda > 0.05 R$ por segundo
                                #     await enviar_telegram(f"🚨 Aceleração de perda em {ativo}: {velocidade_perda:.2f} R$/s | diff atual: {diff:.2f}")
                            
                            
                            ultimo_diff[ativo] = (diff, now)
                    else:
                        # Primeira vez que vemos este ativo
                        ultimo_diff[ativo] = (diff, now)
                    # ========== FIM do monitoramento ==========

                    print(f"Monitorar do diff {ativo}:", ultimo_diff[ativo]  )

                    
                    # rates = mt5.copy_rates_from_pos(ativo, mt5.TIMEFRAME_M2, 0, 5)  # pelo menos 3 candles
                    # if rates is not None or len(rates) > 3:
                    #     df = pd.DataFrame(rates)
                    #     velocidade, aceleracao = calcular_velocidade_aceleracao(df, intervalo_minutos=2)
                    #     LIMIAR_ACELERACAO = 10   # R$/hora², ajuste conforme necessário
                       

                    #     if abs(aceleracao) > LIMIAR_ACELERACAO:
                            
                    #         print(f"Velocidade: {velocidade:.2f} R$/h | Aceleração brusca: {aceleracao:.2f} R$/h²")
                    #         # aqui você pode acionar seu alarme ou lógica de pânico



                    

                    #condicao_PAUSA= (tipo, (tipo_op(ativo)).lower() ,  positivo5  ) in [('compra', 'call' ,'v'), ('venda', 'call' ,'^'),('venda', 'put' ,'v'), ('compra', 'put' ,'^')]
                    condicao_PAUSA= (tipo, (tipo_op(ativo)).lower() ,  positivo5, msg_panico5, sentido_posi5  ) in [('compra', 'call' ,'v','v','v'), ('venda', 'call' ,'^','^','^'),('venda', 'put' ,'v','v','v'), ('compra', 'put' ,'^','^','^')]


                    #anterior = ultimo_positivo5.get(ativo.upper()[:4])  # pode ser None ou ("^", 25.43)
                    anterior = ultimo_positivo5.get(ativo.upper())
                    if anterior:
                        positivo5_anterior, preco_anterior = anterior
                    else:
                        positivo5_anterior, preco_anterior = None, None


                    if positivo5 in ("^", "v") and positivo5 != positivo5_anterior:
                        
                        
                        hora = datetime.datetime.now().strftime("%H:%M:%S")
                        #hora = datetime.now().strftime("%H:%M:%S")
                        #direcao5 = "acima da máxima" if positivo5 == "^" else "abaixo da mínima"
                        direcao5 = positivo5 
                        # Monta a mensagem com preço atual, preço anterior e diferença
                        if preco_anterior is not None:
                            variacao = preco - preco_anterior
                            mensagem = (f"[{hora}] ROMpimento de saída em {ativo}: preço {direcao5}\n"
                                        f"         Preço atual: {preco:.2f} | Anterior: {preco_anterior:.2f} | Variação: {variacao:+.2f}\n")
                        else:
                            mensagem = (f"[{hora}] ROMpimento de saída em {ativo}: preço {direcao5}\n"
                                        f"         Preço atual: {preco:.2f} (sem referência anterior)\n")
    
                        print(mensagem.strip())                       
                        
                        # Salva no arquivo com o nome do ativo (ex: "PETR4.txt")
                        nome_arquivo = f"{ativo.upper()[:4]}_{ativo}.txt"   # ajuste o slicing conforme seu padrão
                        with open(nome_arquivo, 'a', encoding='utf-8') as f:
                            f.write(mensagem)



                        
                    #ultimo_positivo5[ativo.upper()[:4]] = (positivo5, preco)
                    ultimo_positivo5[ativo] = (positivo5, preco)



                    if dados.get("ultimo_status") != status:
                        
                        if dados.get("ultimo_status")=='negativo' : 
                            print ("Mudou")
                            #m9_direcao, impulso, cruzamentos, tendencia_diff, recomendacao, tipo_vela, acho, pavio = 
                 # return direcao, impulso, cruzamentos, tendencia_diff, recomendacao, tipo_vela, acho, pav_sombra
                            # ddrsi= determinar_direcao_RSI(ativo,3)  
                            
                            # impulso=ddrsi[1]#('impulso')                       
                            # pavio=ddrsi[7]#('pav_sombra')

                            app=  analise_pressao_preco(ativo, True)
                            app_direcao = app.get('direcao')
                            app_forca = app.get('forca')

                            ep= expectativa_precos(ativo, True, 0.001)
                            ep_expectativa = ep.get ("expectativa")
                            ep_intensidade =ep.get ("intensidade")


                            dados["historico"] = f"{app_direcao,app_forca, impulso, pavio, ep_expectativa, ep_intensidade}"  #+=           
                                                    
                        
                        dados["ultimo_status"] = status
                        
                           
                        
                        
                        
                        salvar_ativos()
                        await enviar_telegram(f"{ativo} mudou para {status.upper()} ({tipo}) | Entrada:{entrada:.2f} | Atual:{preco:.2f} | Qtd:{qtd}")

                      
                    
                    condicao_caveira=  infoATIVOS.get("status") in ['FECHAR OPERACAO', 'CAVEIRA']
                    
                    bracket = infoATIVOS.get("trivelas")  #("bracket")
                                        
                    
                    terceira_letra = bracket[2] if bracket and len(bracket) >= 3 else None


                    
                    #original aqui condicao_FECHAR_OPERACAO = (tipo, (tipo_op(ativo)).lower() , condicao_caveira ,pavio, terceira_letra) in [('compra', 'call',True ,'LV', 'r'), 
                    #                                                                                                                                       ('venda', 'call',True ,'T^','g'), 
                    #                                                                                                                                       ('venda', 'put',True ,'LV', 'r'), 
                    #                                                                                                                                       ('compra', 'put',True ,'T^','g')   ]
                                                                                #convertia o pavio para maiusculo
                    condicao_FECHAR_OPERACAO = (tipo, (tipo_op(ativo)).lower() , pavio , terceira_letra) in [('compra', 'call' ,'LV', 'r'), 
                                                                                                                    ('venda', 'call' ,'T^','g'), 
                                                                                                                    ('venda', 'put' ,'LV', 'r'), 
                                                                                                                    ('compra', 'put' ,'T^','g')   ]
                    #terceira_letra.lower()

                    #condicao_FECHAR_OPERACAO = (tipo, (tipo_op(ativo)).lower() , pavio) in [('compra', 'call' ,'LV'), 
                    #                                                                                ('venda', 'call' ,'T^'), 
                    #                                                                                ('venda', 'put' ,'LV'), 
                    #                                                                                ('compra', 'put' ,'T^')   ]
                    
                    # condicao_FECHAR_OPERACAO = (
                    #                             (tipo == 'compra' and tipo_op(ativo).lower() == 'call' and pavio == 'LV' and terceira_letra in ['+', 'r']) or
                    #                             (tipo == 'venda' and tipo_op(ativo).lower() == 'call' and pavio == 'T^' and terceira_letra in ['+', 'g']) or
                    #                             (tipo == 'venda' and tipo_op(ativo).lower() == 'put' and pavio == 'LV' and terceira_letra in ['+', 'g']) or
                    #                             (tipo == 'compra' and tipo_op(ativo).lower() == 'put' and pavio == 'T^' and terceira_letra in ['+', 'r'])
                    #                         )


                    condicao_adversa = (tipo, (tipo_op(ativo)).lower() , pavio,(terceira_letra or '').upper()) in [('compra', 'call','LV', 'R'), 
                                                                                                            ('venda', 'call' ,'T^','G'), 
                                                                                                            ('venda', 'put' ,'LV', 'R'), 
                                                                                                            ('compra', 'put' ,'T^','G') ] and status=="negativo" and diff < 0 and abs(diff) > PREJUIZO_MAX_ZERADO
                    #print(f"condicao adversa para {ativo} {condicao_adversa}") """infoATIVOS.get("seta")""" 

                   #============================================================
                    # ===== NOVO: TRAILING STOP =====
                    # ============================================================
                    if TRAILING_ATIVADO: #fepe
                        # Inicializa trailing stop se não existir para este ativo
                        if ativo not in trailing_stops:
                            trailing_stops[ativo] = TrailingStop(distancia=DISTANCIA_TRAILING)
                            trailing_stops[ativo].configurar(entrada, tipo)
                        
                        # Verifica se deve sair pelo trailing stop
                        trailing = trailing_stops[ativo]
                        if trailing.verificar_saida(preco) == 'SAIR' and status == "positivo"  and diff>qtd/100  :
                            print(f"🔴 TRAILING STOP disparado em {ativo}!")
                            
                            # Fecha a operação
                            if mini_stop_pct == IDENTIFICADOR_ROBO:
                                dados["historico"] += f"|FECHOU POR TRAILING STOP| "
                                resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                                await enviar_telegram(f"🔴 TRAILING STOP em {ativo}: {resposta}")
                            else:
                                await enviar_telegram(f"⚠️ ALERTA TRAILING STOP em {ativo}! Preço: {preco:.2f}")
                            
                            # Reseta trailing para próxima operação
                            trailing_stops[ativo].reset()
                            continue  # Pula o resto do loop para este ativo
                    #----------------------------------------------------------------------------------------------------------------            
                    # if TRAILING_ATIVADO:
                    #     # Lista de ativos a monitorar: a opção (real) e o principal (simulado)
                    #     ativos_para_trailing = [ativo]
                    #     principal = ativo_principal(ativo)  # extrai o subjacente, ex: "PETR4"
                        
                    #     # Se houver um principal válido e diferente da opção, adiciona à lista
                    #     if principal and principal != ativo:
                    #         ativos_para_trailing.append(principal)
                        
                    #     # Itera sobre cada um (opção e, se existir, principal)
                    #     for ativo_atual in ativos_para_trailing:
                    #         # Obtém o preço atual do ativo (cada um tem seu próprio preço)
                    #         preco_atual = preco_real(ativo_atual, tipo)  # 'tipo' pode ser 'opcao' ou 'acao'
                            
                    #         # Inicializa trailing stop se não existir para este ativo
                    #         if ativo_atual not in trailing_stops:
                    #             # Para a opção, o preço de entrada é o da abertura da posição (guardado em ENTRADAS)
                    #             # Para o principal, usamos o preço do principal no momento da abertura da opção
                    #             if ativo_atual == ativo:  # é a opção
                    #                 preco_entrada = ATIVOS.get(ativo, {}).get('entrada')
                    #             else:  # é o principal simulado
                    #                 # Guardamos o preço do principal no momento da entrada da opção
                    #                 preco_entrada = ATIVOS.get(ativo, {}).get('entrada_principal')
                                
                    #             # Se por algum motivo não tiver, usa o preço atual (fallback)
                    #             if preco_entrada is None:
                    #                 preco_entrada = preco_atual
                                
                    #             trailing_stops[ativo_atual] = TrailingStop(distancia=DISTANCIA_TRAILING)
                    #             trailing_stops[ativo_atual].configurar(preco_entrada, tipo)  # tipo: 'compra' ou 'venda'
                            
                    #         # Verifica se deve sair pelo trailing stop
                    #         trailing = trailing_stops[ativo_atual]
                    #         if (trailing.verificar_saida(preco_atual) == 'SAIR' 
                    #             and status == "positivo"  # supondo que status é da opção (global)
                    #             and diff > qtd/100):      # diff também da opção (global)
                                
                    #             print(f"🔴 TRAILING STOP disparado em {ativo_atual}!")
                                
                    #             # ============================================================
                    #             # LÓGICA DE SAÍDA (diferente para opção e principal simulado)
                    #             # ============================================================
                    #             if ativo_atual == ativo:
                    #                 # É a opção real: fecha a operação normalmente
                    #                 if mini_stop_pct == IDENTIFICADOR_ROBO:
                    #                     dados["historico"] += f"|FECHOU POR TRAILING STOP (opção)| "
                    #                     resposta = finalizar_ativo(ativo, preco_atual)
                    #                     await enviar_telegram(f"🔴 TRAILING STOP na opção {ativo}: {resposta}")
                    #                 else:
                    #                     await enviar_telegram(f"⚠️ ALERTA TRAILING STOP na opção {ativo}! Preço: {preco_atual:.2f}")
                    #             else:
                    #                 # É o principal simulado: fecha a opção usando o preço da opção (não o do principal)
                    #                 # Motivo: o principal disparou, então devemos sair da opção ao preço atual dela.
                    #                 preco_opcao = preco_real(ativo, tipo)  # preço atual da opção
                    #                 if mini_stop_pct == IDENTIFICADOR_ROBO:
                    #                     dados["historico"] += f"|FECHOU POR TRAILING STOP (principal simulou)| "
                    #                     resposta = finalizar_ativo(ativo, preco_opcao)
                    #                     await enviar_telegram(f"🔴 TRAILING STOP (principal {principal}) disparou! Opção {ativo} fechada a {preco_opcao:.2f}: {resposta}")
                    #                 else:
                    #                     await enviar_telegram(f"⚠️ ALERTA: principal {principal} disparou trailing! Opção {ativo} deveria ser fechada.")
                                
                    #             # Reseta os trailing stops de AMBOS (opção e principal) para não re-disparar
                    #             for ativo_reset in ativos_para_trailing:
                    #                 if ativo_reset in trailing_stops:
                    #                     trailing_stops[ativo_reset].reset()
                    #                     # Remove do dicionário para que na próxima entrada seja reiniciado
                    #                     del trailing_stops[ativo_reset]
                                
                    #             # IMPORTANTE: após fechar a opção, ela é removida de ATIVOS (dentro de finalizar_ativo)
                    #             # e também removemos o principal simulado de qualquer estrutura de monitoramento.
                    #             # Como o principal não está em ATIVOS, não precisamos removê-lo de lá.
                                
                    #             # Sai do loop, pois a opção já foi fechada (não precisamos verificar outros ativos)
                    #             break                                


                    #----------------------------------------------------------------------------------------------------------------

                    if condicao_FECHAR_OPERACAO or condicao_adversa: 
                        NOVA_MSG= (f"FECHAR A OPERACAO EM {ativo} condicao fecha {condicao_FECHAR_OPERACAO }e condicao adv {condicao_adversa}  ")
                        print ( f"FECHAR A OPERACAO EM {ativo} condicao fecha {condicao_FECHAR_OPERACAO }e condicao adv {condicao_adversa}  " )

                    
                    if status in ['positivo', 'negativo'] and (condicao_FECHAR_OPERACAO or condicao_PAUSA) and dentro_horario():    
                    #if status in ['positivo', 'negativo'] and condicao_FECHAR_OPERACAO  and dentro_horario() :
                        #os.system('cls' if os.name == 'nt' else 'clear')
                        print(f"Fim condicoes adversas {ativo} - Robô - humano" )
                        if mini_stop_pct == IDENTIFICADOR_ROBO and FINALIZAR_OP_ROBO_STOP_LOSS:
                            dados["historico"] +=f"|FECHOU POR fechado em adversas1|{pavio} {terceira_letra} pausa {condicao_PAUSA} "
                            resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                            if condicao_PAUSA  and diff>=0 :                    
                                PAUSADO[ativo] =( tipo, (tipo_op(ativo)).lower() ,  positivo5 )
                                nome_arquivo = f"Pausado_{ativo}.txt"   # ajuste o slicing conforme seu padrão
                                with open(nome_arquivo, 'a', encoding='utf-8') as f:
                                    f.write(f"{tipo}, {(tipo_op(ativo)).lower()}, {positivo5}\n")


                            
                            await enviar_telegram("Fim por condicao adversa",resposta)                        
                            print ( f"fechar a operacao de {ativo}  {condicao_FECHAR_OPERACAO}")  #COLOCAR A SAIDA AQUI DEPOIS )

                            
                                    

                                    




                            
                        else:
                            resposta = f"⚠️ ALERTA STOP CONDICAO ADVERSA HUMANA em {ativo} pois \n {tipo} {(tipo_op(ativo))} {pavio.upper()} {terceira_letra} \n pausa:{condicao_PAUSA}!" 
                            await enviar_telegram(resposta)

                    


                    elif status == "positivo":
                        mini_stop_valor = dados["max_diff"] * (1 - mini_stop_pct/100.0)
                        max_mini_stop_valor= dados["max_diff"] * (1 - 35/100.0)
                        
                        
                        if diff > dados.get("max_diff", 0.0):
                            dados["max_diff"] = diff
                            
                            
                           

                            
                            
                            salvar_ativos()
                        else:
                            #os.system('cls' if os.name == 'nt' else 'clear')
                                                       
                            #mini_stop_pct = dados.get("mini_stop_pct", 30.0)
                            #mini_stop_valor = dados["max_diff"] * (1 - mini_stop_pct/100.0)
                            #max_mini_stop_valor= dados["max_diff"] * (1 - 35/100.0)

                            

                            if (dados["stop_loss_pct"] == STOP_LOSS_PADRAO): #and diff >= (qtd * STOP_LOSS_PADRAO_POSITIVO)):
                            
                                stop_loss_pct= STOP_LOSS_PADRAO_POSITIVO
                                dados["stop_loss_pct"]= stop_loss_pct
                                fator = 1 - stop_loss_pct/100.0 if tipo == "compra" else 1 + stop_loss_pct/100.0
                                dados["stop_loss_valor"]=entrada * fator 
                                salvar_ativos()
                            

                            if diff < mini_stop_valor and dados["max_diff"] > 0 and diff>qtd/100    and dentro_horario() :
                          
                            #original, testar com condicaoPausa   if diff < mini_stop_valor and dados["max_diff"] > 0 and diff>qtd/100 and dentro_horario() :
                                
                                #se for robo PAUSAR A CONTAGEM E MUDAR PARA OUTRA COR
                                


                                if mini_stop_pct==IDENTIFICADOR_ROBO and FINALIZAR_OP_ROBO_STOP_MINI_SL and diff < max_mini_stop_valor:
                                    dados["historico"] +=f"|FECHOU POR fechado em MAX mini stop| PAUSA{ condicao_PAUSA} " #, f"Ganho atual: {diff:.2f} < Mini Stop: {mini_stop_valor:.2f} ({mini_stop_pct:.1f}% abaixo do máximo)|"
                                    
                                    print(diff, str(qtd/100))
                                    resposta= finalizar_ativo(ativo, preco_real(ativo, tipo )  )
                                    
                                    await enviar_telegram(resposta)
                                
                                
                                
                                elif mini_stop_pct==IDENTIFICADOR_ROBO and FINALIZAR_OP_ROBO_STOP_MINI_SL and condicao_PAUSA  :
                                    dados["historico"] +=f"|FECHOU POR fechado em mini stop| PAUSA{ condicao_PAUSA} " #, f"Ganho atual: {diff:.2f} < Mini Stop: {mini_stop_valor:.2f} ({mini_stop_pct:.1f}% abaixo do máximo)|"
                                    
                                    print(diff, str(qtd/100))
                                    resposta= finalizar_ativo(ativo, preco_real(ativo, tipo )  )
                                    
                                    await enviar_telegram(resposta)
                                #elif 
                                
                                
                                
                                # elif mini_stop_pct==IDENTIFICADOR_ROBO and (tipo, (tipo_op(ativo)).lower() ,  positivo5  ) in [('compra', 'call' ,'v'), ('venda', 'call' ,'^'),('venda', 'put' ,'v'), ('compra', 'put' ,'^')]:
                                    
                                #     PAUSADO[ativo] =( tipo, (tipo_op(ativo)).lower() ,  positivo5 )
                                #     nome_arquivo = f"Pausado_{ativo}.txt"   # ajuste o slicing conforme seu padrão
                                #     with open(nome_arquivo, 'a', encoding='utf-8') as f:
                                #         f.write(f"{tipo}, {(tipo_op(ativo)).lower()}, {positivo5}\n")

                                
                                


                                else:
                                    critico= 'ALERTA MAXIMO SAIA AGORA!!!! \n' if  diff < max_mini_stop_valor else ""
                                    
                                    await enviar_telegram(
                                        f"⚠️ ALERTA MINI STOP atingido em {ativo}! \n {critico}"
                                        f"Ganho atual: {diff:.2f} < Mini Stop: {mini_stop_valor:.2f} ({mini_stop_pct:.1f}% abaixo do máximo)" )
                                        
                                
                                try:
                                    winsound.Beep(1000, 500)  # beep diferenciado para mini stop
                                except:
                                    pass


                    
                       
                    elif status == "negativo":
                        #'max_diff_zerado: (0.4 >', 0.0, -12.499999999999956,      '< -',          250.0, '\n')
                        
                        #'VALEQ794', 'max_diff_zerado: ', 2.5000000000000133, 'preju', -1.4999999999999902, '< -', 25.0, '\n'
                        #print (( ativo, "max_diff_zerado: ", dados.get("max_diff", 0.0),   "preju" ,   diff   ,    " abs ",abs(diff), '>'  , PREJUIZO_MAX_ZERADO, "\n") *100)  
                        
                        
                        #modificado para perder menos se entrada ruim  
                        #max_ganho= dados.get("max_diff", 0.0)
                        condicao_1 = (0.4 > dados.get("max_diff", 0.0)) and (diff < -PREJUIZO_MAX_ZERADO)                        
                        condicao_2 = mini_stop_pct == IDENTIFICADOR_ROBO and FINALIZAR_OP_ROBO_STOP_LOSS and dentro_horario()
                        condicao_3= (preco <= stop_loss_valor)
                        condicao_4 = (preco >= stop_loss_valor)
                        condicao_5 = condicao_FECHAR_OPERACAO
                        condicao_6 = condicao_adversa

                        preju_humano_zerado = (qtd/100) * VL_HUMANO_ZERADO
                        total_pp= abs(stop_loss_valor-preco) * qtd/100
                        teste_preju= total_pp> preju_humano_zerado  #"acima"if total_pp> preju_humano_zerado else "abaixo"

                        cond = { 
                            "tipo_venda": tipo == "venda", 
                            "tipo_compra": tipo == "compra",
                            "e_robo": mini_stop_pct == IDENTIFICADOR_ROBO and FINALIZAR_OP_ROBO_STOP_LOSS and dentro_horario(),
                            "abaixo_stop": preco <= stop_loss_valor,
                            "acima_stop": preco >= stop_loss_valor,                            
                            "max_diff_zerado": (  dados.get("max_diff", 0.0)  < 0.5 ) and (abs(diff) > (preju_humano_zerado)), #and (abs(diff) > (PREJUIZO_MAX_ZERADO)),
                            "max_diff_zerado_humano": (  dados.get("max_diff", 0.0)  < 0.5 ) and (abs(diff) > (preju_humano_zerado)),
                            
                            #"ganhou_e_empatou":(  dados.get("max_diff", 0.0)  > (qtd/100) ) and (abs(diff) > (qtd/100)),
                            
                            "condicao_seta": condicao_FECHAR_OPERACAO,
                            "condicao_adversa": condicao_adversa,
                            "condicao_teste": ( diff<0 and  abs(diff) > (preju_humano_zerado)  )
                        }

                        #if  abs(diff) > (preju_humano_zerado): NOVA_MSG= f" {ativo, preju_humano_zerado} < ", abs(diff)

                        if ( diff<0 and  abs(diff) > (preju_humano_zerado)  ): 
                            #os.system('cls' if os.name == 'nt' else 'clear')

                            NOVA_MSG= f" {ativo, preju_humano_zerado} < ", abs(diff)
                            print(NOVA_MSG)

                        match cond:                       
                            case {"condicao_seta": True, "e_robo": True} | {"condicao_teste": True, "e_robo": True} :
                                os.system('cls' if os.name == 'nt' else 'clear')
                                dados["historico"] += f"|FECHOU POR condicao seta ou teste|"
                                print(f"Fim condicoes adversas {ativo} - Robô")
                                resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                                await enviar_telegram(resposta) 
                                  

                            case {"condicao_adversa": True, "e_robo": True}:
                                os.system('cls' if os.name == 'nt' else 'clear')
                                dados["historico"] += f"|FECHOU POR condicao adversas|"  

                                print(f"Fim condicoes adversas {ativo} - Robô")
                                resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                                await enviar_telegram(resposta)   
                                
                            
                            
                            case {"tipo_venda": True, "acima_stop": True, "e_robo": True}:
                                os.system('cls' if os.name == 'nt' else 'clear')
                                dados["historico"] += f"|FECHOU POR acima stop em venda|"
                                print(f"Fim VENDA {ativo} - Robô {teste_preju} ")
                                resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                                await enviar_telegram(resposta)
                                  
   
                            
                            case {"tipo_venda": True, "max_diff_zerado": True, "e_robo": True}:
                                os.system('cls' if os.name == 'nt' else 'clear')
                                dados["historico"] += f"|FECHOU POR zerado acima do preju maximo|"  

                                print(f"Fim VENDA {ativo} - Robô (max_diff zerado)")
                                resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                                await enviar_telegram(resposta)
                                
                            
                            case {"tipo_compra": True, "abaixo_stop": True, "e_robo": True}:
                                os.system('cls' if os.name == 'nt' else 'clear')
                                dados["historico"] += f"|abaixo do stop em compra|"  
 
                                print(f"Fim COMPRA {ativo} - Robô {teste_preju} ")
                                resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                                await enviar_telegram(resposta)
    
                            
                            case {"tipo_compra": True, "max_diff_zerado": True, "e_robo": True}:
                                os.system('cls' if os.name == 'nt' else 'clear')
                                dados["historico"] += f"|FECHOU zerado acima do preju maximo|"  

                                print(f"Fim COMPRA {ativo} - Robô (max_diff zerado)")
                                resposta = finalizar_ativo(ativo, preco_real(ativo, tipo))
                                await enviar_telegram(resposta)
                                


                            case {"tipo_venda": True,  "e_robo": False,"max_diff_zerado_humano":True } | {"tipo_compra": True, "e_robo": False, "max_diff_zerado_humano":True}:
                                # Operação manual atingindo stop loss
                                #abaixo_stop": preco <= stop_loss_valor,
                                #"acima_stop": preco >= stop_loss_valor, 
                                #os.system('cls' if os.name == 'nt' else 'clear')
                                #dados["historico"] += f"|zerado acima do preju maximo diff humano| "



                                prejuTotal = "acima do stop" if (tipo == "venda" and preco >= stop_loss_valor) else ("abaixo do stop" if (tipo == "compra" and preco <= stop_loss_valor) else "nenhum stop atingido")

                                print("default!!Prejuizpo HUMANO ZERADO ", prejuTotal ,   dados.get("max_diff", 0.0)  ,"< 0.5 & ", abs(diff), ">", preju_humano_zerado  )
                                tipo_stop = "acima" if tipo == "venda" else "abaixo"
                                resposta = f"⚠️ ALERTA STOP LOSS HUMANO ZERADO   atingido em {ativo}!\n {prejuTotal} \n" \
                                        f"Preço atual: {preco:.2f} {tipo_stop} do Stop Loss: {stop_loss_valor:.2f} ({stop_loss_pct:.1f}%)"
                                await enviar_telegram(resposta)
                                
                                try:
                                    winsound.Beep(800, 500)
                                except:
                                    pass
  

                            case {"tipo_venda": True, "acima_stop": True} | {"tipo_compra": True, "abaixo_stop": True}:
                                # Operação manual atingindo stop loss
                                #os.system('cls' if os.name == 'nt' else 'clear')
                                dados["historico"] += f" | acima do stop |"
                                print("default!!Prejuizpo geral" ,   dados.get("max_diff", 0.0)  ,"< 0.5 & ", abs(diff), ">", preju_humano_zerado  )
                                tipo_stop = "acima" if tipo == "venda" else "abaixo"
                                resposta = f"⚠️ ALERTA STOP LOSS atingido em {ativo}!\n" \
                                        f"Preço atual: {preco:.2f} {tipo_stop} do Stop Loss: {stop_loss_valor:.2f} ({stop_loss_pct:.1f}%)"
                                await enviar_telegram(resposta)
                                
                                try:
                                    winsound.Beep(800, 500)
                                except:
                                    pass
                        
     
                                
                    
#------------------------------------------------------------------------------------------------------------------------------------------                

            # ativos observados
            #for ativo, dados in OBSERVAR.items():
            for ativo, dados in list(OBSERVAR.items()):
                vcv=""
                an_hib_decisao="neutro"    
                apuracao=""
                caso=""
                dados["status"] = "indefinido"
                preco = preco_medio(ativo)
                tipo_opcao="" 
                infoObs = tickers_STATUS.get(ativo.upper()[:4], {})
                bracket = infoObs.get("bracket")
                tipo=""
                terceira_letra = bracket[2] if bracket and len(bracket) >= 3 else None
                condicao_caveira=  infoObs.get("status") not in ['FECHAR OPERACAO', 'CAVEIRA']
                seta=infoObs.get("seta")
                lateral= infoObs.get("lateral")
                rompeu=infoObs.get("rompeu")
                
                
                resultado_romp_saida = rompimento_saida(ativo, n=1, timeframe=2)
                rompeu5 = resultado_romp_saida[0]
                positivo5 = resultado_romp_saida[1]
                msg_panico5 = resultado_romp_saida[2]
                sentido_posi5=resultado_romp_saida[3]

                ativos_observados = set(OBSERVAR.keys())
                ativos_ativos = set(ATIVOS.keys())
                apenas_observados = ativos_observados - ativos_ativos


                



                if not dentro_horario():
                    dados["preco_inicial"]=0.0
                
                if dentro_horario() and dados["preco_inicial"]==0.0:
                    dados["preco_inicial"]=preco_medio(ativo)
                
                
                    
                #print(f"aqui {stop_loss_pct}")    
                avisos = ["FECHAR OPERACAO", "RETORNAR OPERACAO" , "MUDOU", "QUEBROU","HULL","CAVEIRA" ] #"(T^)" ,"(?v)" testar
                #preco = preco_medio(ativo)
                
                #verificar qual a ultima caveira preta se put ir apenas em venda de call e compra de puts
                
                if FILTRAR_SINAIS and dados["reset"]==0 and  ativo.upper()[:4] == ATIVO_COM_ALERTA and ALERTA_ATUAL in avisos :#(ALERTA_ATUAL=="HULL" or ALERTA_ATUAL=="CAVEIRA"):
                    print("RESETAR PRECO \n asdfadsfads \n", ALERTA_ATUAL)
                    dados["reset"]=1
                    dados["preco_inicial"]=preco_medio(ativo)

                diff = preco - dados["preco_inicial"]
                                

                if ativo in PAUSADO:
                    NOVA_MSG=(f"A chave {ativo} existe! Valor: {PAUSADO[ativo]}")


                print ("ate aqui sem erro1   SENSIBILIDADE :", SENSIBILIDADE_ENTRADA)

                m9_direcao_k, impulso_k, cruzamentos_k, tendencia_diff_k, recomendacao_kamikazi = determinar_direcao_RSI_kamikazi(ativo)

                m9_direcao, impulso, cruzamentos, tendencia_diff, recomendacao, tipo_vela, acho, pavio = determinar_direcao_RSI(ativo,3)
                
                trivelas= infoObs.get("trivelas")
                direcao_rsi= infoObs.get("direcao_rsi")
                ultima_vela= trivelas[-1] if trivelas and len(trivelas) >= 3 else None  

                #sent_novo = 'negativa' if (pavio != "T^" and infoObs.get('sentido') == 'negativa') else ('positiva' if pavio != "LV" and infoObs.get('sentido') == 'positiva' else 'neutra')
                
                sent_novo = infoObs.get('sentido') if not pavio else (
                                                            'negativa' if (pavio != "T^" and infoObs.get('sentido', '').startswith('negativa')) else (
                                                                'positiva' if (pavio != "LV" and infoObs.get('sentido', '').startswith('positiva')) else 'neutra'
                                                            )
                                                        )
                




                inversao_sentido = infoObs.get("inversao"), infoObs.get("sentido"),"sent_novo:" ,sent_novo ,pavio    
                
                
                #felipe

                #tickers_STATUS[prefixo]["trivelas"] = (v2_nova, v1_nova, v0_nova)
            
                #reversao = verificar_reversao(tripla_antiga[2], v0_nova)

 
                app=  analise_pressao_preco(ativo, True)
                app_direcao = app.get('direcao')
                app_forca = app.get('forca')

                ep= expectativa_precos(ativo, True, 0.001)
                ep_expectativa = ep.get ("expectativa")
                ep_intensidade =ep.get ("intensidade")
                
                ep_master =expectativa_precos(ativo, False, 0.001)

                NOVA_MSG=  ativo_principal(ativo),ep_master.get("expectativa"), ep_master.get ("intensidade"),trivelas, inversao_sentido  

                gap_v=gap_venda(ativo)
                
                dados["int_geral"] = ep_master.get("expectativa") , round(ep_master.get("gap"),2)    #if abs(diff) >= GATILHO_DIFF_PRECO else 0.0 #vcv
                dados["intensidade"] = f"{ep_expectativa}"
                
                print ("ver ss",rompimento_saida(ativo, 1, timeframe=2))

                #app_direcao,app_forca, app_status_ask, app_status_bid = analise_pressao_preco(ativo, True)
                #-------------------------------------------------------------------------------

                #ate aqui sem erro {'status': 'igual_ask'} direcao forca status_ask status_bid {'direcao': 'QUEDA', 'forca': 'forte', 'status_ask': 'abaixo_ask', 'status_bid': 'abaixo_bid'}
                
                
                print(f"ultimo status do ticje:  {ativo.upper()[:4]} ",infoObs.get("micro_tende") ,infoObs.get("status"), infoObs.get("seta"), infoObs.get("teste"),infoObs.get("bracket"),"|" \
                       ,terceira_letra,m9_direcao,impulso,cruzamentos, tendencia_diff, recomendacao, recomendacao_kamikazi, tipo_vela, pavio, gap_v  )

               
                print(f"Na minha opiniao {acho} kamikazi {recomendacao_kamikazi} expectativa{ep_expectativa, ep_intensidade} ")
                #if 'up' in acho: print ("VAI SUBIR ESSA MERDA") 
                print("-"*30, ativo, GATILHO_DIFF_PRECO,"gap do ativo mae:" ,gap_v )
                print ("ate aqui sem erro2", gap_v, app_direcao,app_forca, analise_pressao_preco(ativo, True))

                status1 = "compra" if diff >= 0.01 else ("venda" if diff <= - 0.01 else "neutro")
                
                status = "compra" if diff > 0 else ("venda" if diff < 0 else "neutro")
                
                gap=  gap_preco_real(ativo)
                
                # if UMA_OPCAO_P_LETRA and mini_stop_pct != IDENTIFICADOR_ROBO :
                #     letra_chave = nome_opcao[4].upper()
                #     for existente in ATIVOS.keys():
                #         if existente[4].upper() == letra_chave:
                            
                #             return false
                # uma_letra_robo= (UMA_OPCAO_P_LETRA and mini_stop_pct!=IDENTIFICADOR_ROBO )
                # Retorna True se a condição for atendida (libera robô)
                
                #resultado = UMA_OPCAO_P_LETRA and any(existente[4].upper() == ativo[4].upper() and existente.mini_stop == IDENTIFICADOR_ROBO for existente in ATIVOS.keys())
                
               #original
                resultado = UMA_OPCAO_P_LETRA and any(
                    len(chave) > 4 and len(ativo) > 4 and
                    chave[4].upper() == ativo[4].upper() and 
                    valor["mini_stop_pct"] == IDENTIFICADOR_ROBO 
                    
                    for chave, valor in ATIVOS.items()
                )
                
                contagens = {
                    'kami': sum(1 for chave, valor in ATIVOS.items()
                                if (len(chave) > 4 and len(ativo) > 4 and
                                    chave[4].upper() == ativo[4].upper() and
                                    valor["mini_stop_pct"] == IDENTIFICADOR_ROBO and
                                    valor["ia_resultado"] == "entrada_kami")),
                    'ia': sum(1 for chave, valor in ATIVOS.items()
                            if (len(chave) > 4 and len(ativo) > 4 and
                                chave[4].upper() == ativo[4].upper() and
                                valor["mini_stop_pct"] == IDENTIFICADOR_ROBO and
                                valor["ia_resultado"] != "entrada_kami"))
                }

                # tipo_atual= 'kami'if valor["ia_resultado"] == "entrada_kami" else 'ia'
                total_entradas = contagens['kami'] + contagens['ia']
                # pode_entrar = UMA_OPCAO_P_LETRA_ROBO and (total_entradas < 2) and (contagens[tipo_atual] == 0    )


                # resultado = UMA_OPCAO_P_LETRA and (contagens['kami'] < 2 and contagens['ia'] < 2)

                # contagens = {
                #     tipo: sum(1 for chave, valor in ATIVOS.items()
                #             if (len(chave) > 4 and len(ativo) > 4 and
                #                 chave[4].upper() == ativo[4].upper() and
                #                 valor["mini_stop_pct"] == IDENTIFICADOR_ROBO and
                #                 valor["ia_resultado"] == tipo))
                #     for tipo in ["entrada_kami", "entrada_ia"] }

                # resultado = UMA_OPCAO_P_LETRA and all(contagens[tipo] == 1 for tipo in ["entrada_kami", "entrada_ia"])


                NOVA_MSG+= " kami: ",contagens['kami']," ia:" ,contagens['ia'], sinal2, lista_principais

                
                if (preco and ativo not in ATIVOS 
                    and dados["preco_inicial"]>0.02 and gap <= max(GATILHO_DIFF_PRECO, 0.02)  
                    and AUTOMATIZAR and dentro_horario() and status1 in ['compra', 'venda'] and not resultado ):
                    
                    

                    #gap=  gap_preco_real(ativo)
                    inform = mt5.symbol_info(ativo)
                    resultado_antigo = intensidade_sinal_antiga(ativo, status1)
                    resultado_novo = intensidade_sinal(ativo, status1)
                    sistema = SistemaDecisaoCompleto()
                    analise = sistema.analisar_operacao_completa(ativo, status1, resultado_antigo, resultado_novo, inform)
                    fatores_decisivos = analise.get('decisao_integrada', {}).get('fatores_decisivos', [])
                    #tipo_opcao = analise.get('decisao_integrada', {}).get('detalhes', {}).get('tipo_opcao')
                    #if tipo_opcao==None or tipo_opcao=="": 
                    tipo_opcao = tipo_op(ativo)


                      
                    
                    ana_fim4= analise4_final(ativo, resultado_antigo, resultado_novo, inform)    
                    ana_v= sistema.analisar_operacao_completa(ativo, 'venda', resultado_antigo, resultado_novo, inform)
                    ana_c= sistema.analisar_operacao_completa(ativo, 'compra', resultado_antigo, resultado_novo, inform)


                    
                    print(f"{ativo} {preco} {tipo_opcao} {status1}  fim {ana_fim4} v", ana_v['analise_symbol']['recomendacao_geral']['decisao'], "c ",ana_c['analise_symbol']['recomendacao_geral']['decisao'])

                    
                    vcva= votar_compra_ou_vender_antigo(ativo, inform)
                    melhor_op=obter_melhor_operacao(ativo)
                    vcv=votar_compra_ou_vender(ativo, inform)
                    
                    print("AQUI DAVA ERRO: ", vcv['decisao'], vcv['tamanho_posicao'] , vcv['detalhes'] ,vcv['detalhes']['direcao_tendencia'], 'tipo_opcao:' ,vcva)
                    dados["status"] = status,vcv['tamanho_posicao']

                    #sinal_op_30= sinal_opcoes_30min(ativo)
                    #sinal_op_30_m=sinal_opcoes_30min_melhorado(ativo)
                    #resultado = sinal_opcoes_30min_melhorado(ativo)
                    
                    

                    print("gg"*100)
                    
                    

                    #print( "Aqui teste da funcao nova melhorada" ,sinal_op_30_m.get ("sinal"),sinal_op_30_m.get ("motivo") )
                    
                    #pr=preco_real(ativo, status)

                    stop_loss_pct=     STOP_LOSS_PADRAO   
                        
                    #felipe
                    # ================== ANÁLISE COM IA ==================
                    print(f"\n{'='*60}")
                    print(f"🔍 DEBUG - Analisando {ativo}")
                    print(f"{'='*60}")

                    try:
                        resultado = sinal_opcoes_30min_melhorado(ativo)
                        print(f"✅ resultado obtido com sucesso")
                        print(f"   Tipo de resultado: {type(resultado)}")
                        print(f"   Chaves de resultado: {list(resultado.keys()) if isinstance(resultado, dict) else 'não é dict'}")
                        
                    except Exception as e:
                        print(f"❌ Erro ao chamar sinal_opcoes_30min_melhorado: {e}")
                        import traceback
                        traceback.print_exc()
                        continue

                    # =============================================
                    # 🔍 DEBUG - VERIFICAR estado_ia
                    # =============================================
                    try:
                        #estado_teste = resultado.get('estado', {})
                        estado_ia = resultado.get('estado')
                        print(f"\n📊 estado_ia obtido:")
                        print(f"   Tipo: {type(estado_ia)}")
                        print(f"   É None? {estado_ia is None}")
                        
                        if estado_ia is not None:
                            if isinstance(estado_ia, dict):
                                print(f"   ✅ estado_ia é um DICIONÁRIO")
                                print(f"   Chaves: {list(estado_ia.keys())}")
                                if 'metricas' in estado_ia:
                                    print(f"   ✅ Tem 'metricas'")
                                    print(f"   Métricas: {list(estado_ia['metricas'].keys())}")
                                else:
                                    print(f"   ⚠️ NÃO tem 'metricas'")
                                    print(f"   Chaves disponíveis: {list(estado_ia.keys())}")
                                    
                            elif isinstance(estado_ia, str):
                                print(f"   ⚠️ estado_ia é uma STRING!")
                                print(f"   Conteúdo (primeiros 200 caracteres): {estado_ia[:200]}...")
                                print(f"   🔄 Tentando converter para dict...")
                                try:
                                    estado_ia = json.loads(estado_ia)
                                    print(f"   ✅ Convertido com sucesso para dict!")
                                    print(f"   Chaves: {list(estado_ia.keys())}")
                                except Exception as e:
                                    print(f"   ❌ Erro ao converter: {e}")
                                    estado_ia = None
                            else:
                                print(f"   ❌ estado_ia é do tipo inesperado: {type(estado_ia)}")
                                estado_ia = None
                        else:
                            print(f"   ⚠️ estado_ia é None")
                            
                    except Exception as e:
                        print(f"❌ Erro ao processar estado_ia: {e}")
                        import traceback
                        traceback.print_exc()
                        estado_ia = None

                    # =============================================
                    # 🔍 DEBUG - VERIFICAR resultado['sinal']
                    # =============================================
                    try:
                        sinal = resultado.get('sinal')
                        confianca = resultado.get('confianca')
                        print(f"\n📊 Sinal da IA:")
                        print(f"   Sinal: {sinal}")
                        print(f"   Confiança: {confianca}")
                        print(f"   Tipo de sinal: {type(sinal)}")
                        print(f"   Tipo de confianca: {type(confianca)}")
                    except Exception as e:
                        print(f"❌ Erro ao ler sinal/confianca: {e}")

                    # =============================================
                    # 🔍 DEBUG - PROCESSAR estado_ia
                    # =============================================
                    estado_str = None

                    if estado_ia and isinstance(estado_ia, dict) and 'metricas' in estado_ia:
                        print(f"\n✅ Estado válido para {ativo}")
                        print(f"   Métricas: {list(estado_ia['metricas'].keys())}")
                        
                        try:
                            # Converter diff se for numpy array
                            if isinstance(estado_ia.get('metricas', {}).get('diff'), np.ndarray):
                                estado_ia['metricas']['diff'] = estado_ia['metricas']['diff'].tolist()
                                print("   ✅ Diff convertido para lista")
                            
                            # Serializar com segurança
                            print("   🔄 Serializando estado...")
                            estado_seguro = serializar_estado_seguro(estado_ia)
                            estado_str = json.dumps(estado_seguro, indent=2, ensure_ascii=False)
                            print(f"   ✅ Estado serializado (tamanho: {len(estado_str)} caracteres)")
                            print(f"   ✅ estado_str é string? {isinstance(estado_str, str)}")
                            
                        except Exception as e:
                            print(f"   ❌ Erro ao serializar: {e}")
                            import traceback
                            traceback.print_exc()
                            estado_str = None
                            
                    else:
                        print(f"\n⚠️ Estado INVÁLIDO para {ativo}!")
                        if estado_ia is not None:
                            if isinstance(estado_ia, dict):
                                print(f"   Chaves: {list(estado_ia.keys())}")
                                if 'metricas' not in estado_ia:
                                    print(f"   ⚠️ Falta a chave 'metricas'")
                            else:
                                print(f"   Tipo: {type(estado_ia)} - não é um dicionário")
                        estado_str = None

                    # =============================================
                    # 🔍 DEBUG - VERIFICAR estado_str FINAL
                    # =============================================
                    print(f"\n📊 estado_str final:")
                    print(f"   Tipo: {type(estado_str)}")
                    print(f"   É None? {estado_str is None}")
                    if estado_str:
                        print(f"   Tamanho: {len(estado_str)} caracteres")
                        print(f"   Primeiros 100 caracteres: {estado_str[:100]}...")

                    print(f"{'='*60}")
                    print(f"🔍 FIM DO DEBUG para {ativo}")
                    print(f"{'='*60}\n")
                    
                    
                    
                    
                    
                    
                    
                    # # ================== ANÁLISE COM IA ==================
                    # resultado = sinal_opcoes_30min_melhorado(ativo)                   
                    # print("ver aqui")
                    # estado_ia = resultado.get('estado')
                    # print(estado_ia)
                    # print("fim ver aqui")
                    
                    # # Inicializar
                    # estado_str = None

                    # # =============================================
                    # # 🔥 VERIFICAR E CONVERTER estado_ia COM SEGURANÇA
                    # # =============================================
                    # if estado_ia is not None:
                    #     # Se for string, tentar converter para dict
                    #     if isinstance(estado_ia, str):
                    #         try:
                    #             estado_ia = json.loads(estado_ia)
                    #             print(f"✅ estado_ia convertido de string para dict")
                    #         except json.JSONDecodeError as e:
                    #             print(f"⚠️ Erro ao converter estado_ia: {e}")
                    #             estado_ia = None
                        
                    #     # Agora verificar se é um dicionário válido
                    #     if estado_ia and isinstance(estado_ia, dict):
                    #         if 'metricas' in estado_ia:
                    #             print(f"✅ Estado válido para {ativo}")
                    #             print(f"   Métricas: {list(estado_ia['metricas'].keys())}")
                                
                    #             # =============================================
                    #             # CONVERTER DIFF COM SEGURANÇA
                    #             # =============================================
                    #             if 'metricas' in estado_ia and estado_ia['metricas']:
                    #                 if isinstance(estado_ia['metricas'].get('diff'), np.ndarray):
                    #                     estado_ia['metricas']['diff'] = estado_ia['metricas']['diff'].tolist()
                    #                     print("   ✅ Diff convertido para lista")
                                
                    #             # =============================================
                    #             # SERIALIZAR COM SEGURANÇA
                    #             # =============================================
                    #             estado_seguro = serializar_estado_seguro(estado_ia)
                    #             estado_str = json.dumps(estado_seguro, indent=2, ensure_ascii=False)
                    #             print(f"   ✅ Estado serializado (tamanho: {len(estado_str)} caracteres)")
                                
                    #         else:
                    #             print(f"⚠️ Estado sem 'metricas' para {ativo}")
                    #             print(f"   Chaves: {list(estado_ia.keys())}")
                    #             estado_str = None
                    #     else:
                    #         print(f"⚠️ estado_ia não é um dicionário válido para {ativo}")
                    #         estado_str = None
                    # else:
                    #     print(f"⚠️ estado_ia é None para {ativo}")
                    #     estado_str = None

                    # # =============================================
                    # # 🔥 AGORA USE estado_str PARA SALVAR
                    # # =============================================


                    print("g*g"*100)
                    print(f"📊 estado_str é string? {isinstance(estado_str, str)}")
                    print(f"📊 estado_str é None? {estado_str is None}")
                    if estado_str:
                        print(f"📊 Tamanho: {len(estado_str)} caracteres")


                    # if resultado['sinal'] in ['CALL', 'CALL_FORTE', 'PUT', "PUT_FORTE" ] and resultado['confianca'] > 0.7 : 
                    #     os.system('cls' if os.name == 'nt' else 'clear')
                    #     for ativo in apenas_observados:
                            
                    #         dados_1 = OBSERVAR.get(ativo, {})
                    #         print(f"🔍 {ativo}: {dados_1}")


                    
                    
    
                    # if resultado['confianca'] > 0.7 and gap <= max(GATILHO_DIFF_PRECO, 0.02) and resultado['sinal'] in ['CALL', 'CALL_FORTE', 'PUT', "PUT_FORTE"]:
                    #     tipo = tipo_opcao.lower()
                    #     sinal = resultado['sinal']                        
                    #     status = 'venda' if (tipo != sinal[:3].lower()) else ('compra' if (tipo == sinal[:3].lower()) else 'neutro')                        
                    #     if status != "neutro":
                    #         stop_loss_valor = preco * (1 - stop_loss_pct/100.0) if status == 'compra' else preco * (1 + stop_loss_pct/100.0)                          
                    #         ATIVOS[ativo] = {
                    #             "qtd": QTD_AUTO,
                    #             "entrada": preco_real(ativo, status),
                    #             "tipo": status,
                    #             "stop_loss_pct": STOP_LOSS_PADRAO,
                    #             "stop_loss_valor": stop_loss_valor,
                    #             "ultimo_status": None,
                    #             "max_diff": 0.0,
                    #             "mini_stop_pct": IDENTIFICADOR_ROBO,
                    #             "mute": False,
                    #             "intensidade": 10,
                    #             #"ia_resultado": resultado,      # <-- Guarda a decisão (sinal, confiança)
                    #             "ia_estado": estado_str #estado_ia          # <-- ✅ GUARDA O ESTADO COMPLETO!
                    #         }
                    #         enviar_ordem(ativo, status, QTD_AUTO, "1")
                    #         await enviar_telegram(f"✅ ROBO AQUI 🤖 {status.capitalize()} registrada: {ativo} | Entrada: {preco_real(ativo, status)} | Qtd: {QTD_AUTO} | gap:{gap:.2f} |  IA", "")
                    #         salvar_ativos()

                    print("?"*100)

                    

                    # PRIORIDADE: estado_ia > resultado
                    
                    sinal1 = estado_ia.get('sinal', resultado.get('sinal', ''))
                    decisao1 = estado_ia.get('decisao', resultado.get('decisao', ''))
                    confianca_real = estado_ia.get('confianca', resultado.get('confianca', 0))


                    print (ativo,resultado['confianca'], confianca,confianca_real,"|", resultado['sinal'], sinal, sinal1, decisao1 )
                    
                    print("?"*100)
                    


                    if (confianca_real > 0.7 and gap <= max(GATILHO_DIFF_PRECO, 0.02) and sinal1 in ['CALL', 'CALL_FORTE', 'PUT', "PUT_FORTE"]):

                    #if resultado['confianca'] > 0.7 and gap <= max(GATILHO_DIFF_PRECO, 0.02) and resultado['sinal'] in ['CALL', 'CALL_FORTE', 'PUT', "PUT_FORTE"]:
                        tipo = tipo_opcao.lower()
                        #sent=infoObs.get("sentido")
                        
                        sent = sent_novo
                        #felipe
                        #sent = 'negativa' if (pavio != "T^" and infoObs.get('sentido') == 'negativa') else ('positiva' if pavio != "LV" and infoObs.get('sentido') == 'positiva' else 'neutra')
                        
                        
                        
                        mapeamento = {   
                            ('put', 'CALL' ): 'venda',
                            
                            ('call', 'CALL'): 'compra',
                            
                            ('put', 'CALL_FORTE'): 'venda',
                            
                            ('call', 'CALL_FORTE'): 'compra',
                            
                            
                            ('call', 'PUT'): 'venda',
                            
                            ('put', 'PUT'): 'compra',
                            
                            ('call', 'PUT_FORTE'): 'venda',
                            
                            ('put', 'PUT_FORTE'): 'compra',
                        }

                        status = mapeamento.get((tipo, sinal1), 'neutro')

                        # mapeamento = {   
                        #     ('put', 'CALL', 'positiva' ): 'venda',
                            
                        #     ('call', 'CALL','positiva'): 'compra',
                            
                        #     ('put', 'CALL_FORTE', 'positiva'): 'venda',
                            
                        #     ('call', 'CALL_FORTE', 'positiva'): 'compra',
                            
                            
                        #     ('call', 'PUT', 'negativa'): 'venda',
                            
                        #     ('put', 'PUT',  'negativa'): 'compra',
                            
                        #     ('call', 'PUT_FORTE', 'negativa'): 'venda',
                            
                        #     ('put', 'PUT_FORTE', 'negativa'): 'compra',
                        # }

                        # status = mapeamento.get((tipo, sinal1, sent), 'neutro')

                        # ===== VERSÃO NO SEU ESTILO =====

                        # Definição das regras
                        regras = {
                            ('compra', 'call'): {'pavio': ['LV'], 'vela': ['R'], 'sent': ['negativa']},
                            ('venda', 'call'): {'pavio': ['T^'], 'vela': ['G'], 'sent': ['positiva']},
                            
                            ('compra', 'put'): {'pavio': ['T^'], 'vela': ['G'], 'sent': ['positiva']},
                            ('venda', 'put'): {'pavio': ['LV'], 'vela': ['R'], 'sent': ['negativa']}
                        }

                        # Pega as regras para esta operação
                        r = regras.get((status, tipo))
                        geral=""

                        if r:
                            # Verifica cada componente
                            pavio_proibido = pavio and pavio.upper() in r['pavio']
                            vela_proibida = ultima_vela and ultima_vela.upper() in r['vela']
                            sent_proibido = sent and sent in r['sent']
                            
                            # Monta a mensagem
                            alertas = []
                            if pavio_proibido:
                                alertas.append(f"PAVIO:{pavio}")
                            if vela_proibida:
                                alertas.append(f"VELA:{ultima_vela}")
                            if sent_proibido:
                                alertas.append(f"SENT:{sent}")                            
                            if alertas:
                                geral=(f"PROIBIDA: {', '.join(alertas)}")
                            else:
                                geral=(" PERMITIDA")

                          



                        combinacoes_proibidas = {
                                # ('compra','call' ,'LV',"R" ,'negativa'), ('venda', 'call','G' ,'T^', 'positiva'),
                                # ('compra', 'put', 'T^','G' ,'positiva'),   ('venda','put','R' , 'LV', 'negativa')
                                # ('compra','call' ,'LV','negativa'), ('venda', 'call' ,'T^', 'positiva'),
                                # ('compra', 'put', 'T^','positiva'),   ('venda','put' , 'LV', 'negativa')
                                # ('compra','call' ,'LV'), ('venda', 'call' ,'T^'),
                                # ('compra', 'put', 'T^'),   ('venda','put' , 'LV')

                                ('compra','call' ,'negativa'), ('venda', 'call' , 'positiva'),
                                ('compra', 'put','positiva'),   ('venda','put' ,  'negativa')
                            
                            }
                            #('positiva', True, 'compra', 'put', 'r', 'T^')",
                            # (ultima_vela or '').upper()
                            # 
                        # Uso:
                        
                        proibida, nome_combinacao = is_proibida(status, tipo,  (pavio or '').upper(), (ultima_vela or '').upper(), sent)
                        #msg = is_proibida('PETR4', 'compra', 'call', 'LV', 'R', 'negativa')
                        #print(msg)  # ⚠️ PETR4 em proibidas1

                        if proibida:
                            nome=nome_combinacao
                            NOVA_MSG =(f"{ativo}⚠️ Operação em {nome}  pois {status, tipo, pavio, ultima_vela, sent}")      
                        else : 
                            nome="operacao ok"          
                        #permitido = (status,tipo , (pavio or '').upper(), sent) not in combinacoes_proibidas
                        #permitido = (status, tipo,  sent) not in combinacoes_proibidas and sent != 'neutra' and ultima_vela!='+'
                        
                        # Verifica todas as condições para permitir a operação
                        permitido = (
                            (status, tipo, sent) not in combinacoes_proibidas and  # não está na lista proibida
                            sent != 'neutra' and  # sentimento não é neutro
                            ultima_vela != '+'  # última vela não é de alta
                        )
                        intensao_ai=False
                        if status in ["compra", "venda"]:
                            mensagem_intensidade_ai, percentual_ai, perc_principal_ai = intensidade_sinal(ativo, status)                                                          
                            intensao_ai = sentimento_msg(INTENSAO, mensagem_intensidade_ai)    

                        pode_entrar = UMA_OPCAO_P_LETRA_por_ROBO and (total_entradas < 2) and (contagens['ia'] == 0    )

                        #NOVA_MSG+= "pode_entrar: ", str(pode_entrar)

                        if status!='neutro' and pode_entrar :
                        #original if status!='neutro' and permitido and pode_entrar :
                            stop_loss_valor = preco * (1 - stop_loss_pct/100.0) if status == 'compra' else preco * (1 + stop_loss_pct/100.0)
                            

                            ATIVOS[ativo] = {
                                "qtd": QTD_AUTO,
                                "entrada": preco_real(ativo, status),
                                "tipo": status,
                                "stop_loss_pct": STOP_LOSS_PADRAO,
                                "stop_loss_valor": stop_loss_valor,
                                "ultimo_status": None,
                                "max_diff": 0.0,
                                "mini_stop_pct": IDENTIFICADOR_ROBO,
                                "mute": False,
                                "intensidade": 10,
                                "ia_resultado": f"{nome, geral ,sent,permitido, status,tipo ,ultima_vela, pavio, intensao_ai}",
                                "ia_estado": estado_str
                            }                    #"('operacao ok', 'PROIBIDA: VELA:g, SENT:positiva', 'positiva', True, 'venda', 'call', 'g', 'lv')",
                            
                            enviar_ordem(ativo, status, QTD_AUTO, "1")
                            await enviar_telegram(f"✅ ROBO AQUI 🤖  {status.capitalize()} registrada: {ativo} tipo: {tipo, ultima_vela, pavio} sinal: {sinal1, decisao1, intensao_ai } | Entrada: {preco_real(ativo, status)} | Qtd: {QTD_AUTO} | gap:{gap:.2f} | Permitido:{permitido} |IA versao {nome_programa }", "")
                            salvar_ativos()

      
                    else: 
                        if gap>GATILHO_DIFF_PRECO: print(f"GAP ALTO {gap}")
                        elif resultado['confianca'] < 0.7: print (f"confianca abaixo de 0.7 ", resultado['confianca']  )
                        elif (resultado['sinal'], pavio) in [ ('PUT', "T^" ) , ("PUT_FORTE", "T^"),('CALL', "LV"), ('CALL_FORTE',"LV")]: print( "sinal e pavio contrario ", resultado['sinal'], pavio   )
                        stats = rede.get_estatisticas()
                        print(f"📊 Taxa de acerto: {stats['taxa_acerto']:.1f}%")

                       




                        # # 4. Após fechar operação, registrar resultado
                        # lucro_percentual = (preco_saida - preco_entrada) / preco_entrada * 100
                        # recompensa = rede.registrar_resultado(estado, lucro_percentual)
                        
                        # print(f"💰 Lucro: {lucro_percentual:.2f}% | Recompensa: {recompensa:.2f}")
                        
                        # # 5. Ver estatísticas atualizadas
                        




                    # Verifica se é um dicionário válido
                    if isinstance(vcv, dict) and vcv is not None: 
                        decisao = vcv.get('decisao', 'indefinido')
                        tamanho = vcv.get('tamanho_posicao', 0)
                        detalhes = vcv.get('detalhes', {})
                        direcao = detalhes.get('direcao_tendencia', 'desconhecida') if isinstance(detalhes, dict) else 'erro'
                        
                        print("."*10)
                        print("aqui olha aqui \n", "%"*20)
                        print(decisao, tamanho, detalhes, direcao, 'vcva:', vcva, "melhor:", melhor_op)
                    else:
                        print(f"Erro: vcv é {vcv} (tipo: {type(vcv)}). Não é um dicionário válido.")
                        # Decida um comportamento alternativo (ex: não faz nada, usa valores padrão, etc.)

                    
                    #print ("@.."*20,"\n DECISAO:",ativo,status1,analise['analise_symbol']['recomendacao_geral']," gap:",gap, f"{(GATILHO_DIFF_PRECO+0.01)}" ,"aqui",fatores_decisivos, "decisao 4" ,decisao4 ,"%"*200)
                    #print("ver se vem daqui VCV",vcv['decisao'],"STATUS1=", status1 ,vcv['tamanho_posicao'] ,  'tipo_opcao??:' ,vcva, "mELHOR OP:", melhor_op)
                    #print("analise:", analise['analise_symbol']['recomendacao_geral']['decisao'])
                    
                    #print ( tipo_opcao ,"tipo"     )#resultados[decisao_final]["tipo_opcao"]
                    #print("."*10)
                    #diff = preco - dados["preco_inicial"]
                    #anhib= analise_hibrida_completa(ativo, status)
                    #venda POSIÇÃO MODERADA {'direcao_tendencia': 'ALTA', 'tipo_opcao': 'CALL', 'score': 0} tipo_opcao: venda
                    #if (vcv["decisao"], status1) in [('compra', 'venda'), ('venda', 'compra')]: 
                                            

                    #if (vcv["decisao"], status1) in [('compra', 'compra'), ('venda', 'venda')]: 
                        
                    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ RETIRADO PARA TESTE DE FLUIDEZ  
                    # condicao_oposta = (vcv["decisao"], status1) in [('compra', 'venda'), ('venda', 'compra')]
                    
                    # #MUDANCA DE ONTEM PRA HJ TESTAR IGUALDADE.
                    # condicao_igual = (vcv["decisao"], status1, melhor_op) in [('compra', 'compra', 'compra'), ('venda', 'venda', 'venda')]

                                        
                    
                    # if condicao_oposta:
                    #     #print ("vou resetar o preco \n"*20)
                    #     dados["reset"]=1
                    #     dados["preco_inicial"]=preco_medio(ativo)

                    # if condicao_igual:
                    #     #print ("AMBOS DE ACORDO \n"*20)
                    #     analise['analise_symbol']['recomendacao_geral']['decisao']
                        
                    #     decisao4= analise['analise_symbol']['recomendacao_geral']['decisao'] #'EXECUTAR'# faz outra coisa
                    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    


                    status = "compra" if diff > 0 else "venda"
                    #mudei aqui e subi para qye a verificacao seja feita apos mudanca de preco status1 = "compra" if diff >= GATILHO_DIFF_PRECO else "venda" if diff <= -GATILHO_DIFF_PRECO else "neutro"
                    #status=vcv if vcv in ["venda","compra"] else "indeterminado"
                    
                    dados["reset"]= 0 if abs(diff) > 0 else 1 
                    
                    #mensagem_intensidade, percentual, perc_principal = intensidade_sinal(ativo, status1)                                  
                    #mensagem_intensidade_a, percentual_a, perc_principal_a = intensidade_sinal_antiga(ativo, status1)
                        
                    #dados["intensidade"] = percentual #if abs(diff) >= GATILHO_DIFF_PRECO else 0.0 #status
                    #dados["int_geral"] = perc_principal #if abs(diff) >= GATILHO_DIFF_PRECO else 0.0 #vcv 
                    
                    """if status1 in ["venda", "compra"]:
                        an_hib_st1=  analise_hibrida_completa(ativo, status1)
                        print(f"{ativo} aqui status1:{status1}{diff} {an_hib_st1['decisao_final'] } \n"   ) 

                    if status in ["venda", "compra"]:
                        an_hib_st_v=  analise_hibrida_completa(ativo, "venda")
                        an_hib_st_c=  analise_hibrida_completa(ativo, "compra")
                        print(f"{ativo} aqui status:{status}{diff} {an_hib_st_v['decisao_final'] } | {an_hib_st_c['decisao_final'] } \n"   ) 
                    """
                    #an_hib_vcv= analise_hibrida_completa(ativo, vcv)


                    #print("0"*100)
                    #print(f"{ativo}---\n--{vcv['decisao']}---\n---{percentual}-vcv antigo-{vcva}- \n status --{status}-status1 {status1}--Melhor operacao:--{obter_melhor_operacao(ativo)}")
                    
                    #print(f"{ativo} aqui asdasdfdasdf:{status}{diff} {an_hib_st['decisao_final'] } \n"   )
                    #print(f"{ativo} aqui asdasdfdasdf:{status1}{diff} \n    status: {status} {an_hib_st['decisao_final']} \n vcv: {vcv} {an_hib_vcv['decisao_final']} "   )
                    #if dados["status"] != status and abs(diff) >= GATILHO_DIFF_PRECO  or dados["intensidade"]>=LIMIAR_FORCA :
                    #    dados["status"] = status

                    melhores_condicoes = {
                                        ('compra', 'call', 'T^', 'G'),
                                        ('compra', 'call', 'T^', 'g'),
                                        ('venda', 'call', 'LV', 'R'),
                                        ('venda', 'call', 'LV', 'r'),
                                        ('compra', 'put', 'LV', 'R'),
                                        ('compra', 'put', 'LV', 'r'),
                                        ('venda', 'put', 'T^', 'G'),
                                        ('venda', 'put', 'T^', 'g')
                                    }

                     



                    estados_micro_tendencia= [ ("CAVEIRA_G", "put", "venda"),("CAVEIRA_G", "call", "compra"),("CAVEIRA_R", "put", "compra"),("CAVEIRA_R", "call", "venda"),("CIMA", "put", "venda"),
                                                                                                          ("CIMA", "call", "compra"),
                                                                                                          ("BAIXO", "put", "compra"),
                                                                                                          ("BAIXO", "call", "venda"),                                                                                                       
                                                                                                          
                                                                                                          ("HULL_G", "put", "venda"),
                                                                                                          ("HULL_G", "call", "compra"),
                                                                                                          ("HULL_R", "put", "compra"),
                                                                                                          ("HULL_R", "call", "venda")     ]

                    estados_seta= [('compra', 'call', 'LV',  'R' ),
                                                                                                                                       
                                                                                                                                       
                                ('compra', 'call', 'LV',  '+' ), 
                                ('venda', 'call', 'T^', 'g'),
                                ('venda', 'call', 'T^', 'G'),
                                
                                #('venda', 'call', None, 'g'),
                                #('venda', 'call', None, 'G'),
                                
                                
                                ('venda', 'call', 'T^', '+'), 
                               
                               
                                ('compra', 'put', 'T^', 'G'),
                                ('compra', 'put', 'T^', '+'), 
                                ('venda', 'put', 'LV', 'R'),
                                ('venda', 'put', 'LV', 'r'),
                                
                                #('venda', 'put', None, 'R'),
                                #('venda', 'put', None, 'r'),
            
                                
                                
                                ('venda', 'put', 'LV', '+')  ]

                    # Calcular condições
                    #decisao_case= "neutro"
                                        
                    

                    ambas_op_full=analisar_ambas_operacoes(ativo)
                    ambas_op= ambas_op_full['melhor_operacao']
                    mensagem_ambas = ambas_op_full['mensagem']                            


                                        
                    primeiro=None
                    
                    saidas_possiveis = [ ambas_op,vcva, status1, melhor_op, ana_fim4.lower()]
                    kami_baixa=["COMPRA DE PUT","COMPRA DE PUT (moderada)","VENDA DE CALL (estratégia conservadora)"] 
                    kami_alta=[ "COMPRA DE CALL", "COMPRA DE CALL (moderada)","VENDA DE PUT (estratégia conservadora)"  ]


                    print ("ate aqui sem erro3")
                    #rompe= rompimento_saida(ativo, 1, timeframe=2)
                # rompeu=rompe[0]
                # direcao_rompe=rompe[1]


                    sensibilidade = SENSIBILIDADE_ENTRADA
                    expectativaK = ep_master.get("expectativa", 'NEUTRO')
                                        



                    if recomendacao_kamikazi in kami_alta + kami_baixa :
                        for saida in saidas_possiveis:
                            
                            # DESLIGADA AS PROTEÇÕES AQUI
                            
                            
                            condicao_alta = (tipo_vela.startswith('positiva') 
                                            #and pavio.upper() != "LV" 
                                            and (pavio or '').upper()!="LV"
                                            #and positivo5 !="v"
                                            #and msg_panico5 =="^"  #testar a consolidacao do sinal
                                            
                                            # and app_direcao=='ALTA'  
                                            #and ep_master.get("expectativa") !='QUEDA'#USANDO AQUI
                                            and expectativaK !='QUEDA'
                                            #and terceira_letra.upper()!="R"
                                            #and ultima_vela.upper()!="R" 
                                            and terceira_letra not in ("R", "r")
                                            and ultima_vela not in ("R", "r")
                                            
                                            
                                            # and impulso not in ["ACELERAÇÃO DE BAIXA (RSI se afastando para baixo)","APROXIMAÇÃO POR CIMA (RSI descendo em direção à MA)","IMPULSO INDEFINIDO (oscilação sem direção clara)"] 
                                            and (recomendacao_kamikazi in kami_alta) 
                                            and (tipo_opcao.lower(), saida, app_direcao) in [('call', 'compra','ALTA'), ('put', 'venda','QUEDA' )]
                                            and ( (( sensibilidade, positivo5, msg_panico5, sentido_posi5, ep_master.get("expectativa"), (ultima_vela or '').upper() ) in [ (4,'^','^','^','ALTA', 'G')  ]  and "AGUARDAR" not in recomendacao ) or  
                                                
                                                
                                                (( sensibilidade, positivo5, msg_panico5, sentido_posi5, (ultima_vela or '').upper()    ) in [ (3,'^','^','^', 'G' )  ] and "AGUARDAR" not in recomendacao  ) 
                                                 or (sensibilidade ==2 and positivo5 !="v" and msg_panico5 =="^" and sentido_posi5!= "v" and (ultima_vela or '').upper()=='G' ) #acitavel or (sensibilidade ==1 and positivo5 !="v" and msg_panico5 !="v" and sentido_posi5!= "v" )  
                                                  or (sensibilidade ==1 and positivo5 !="v" and msg_panico5 !="v" and sentido_posi5!= "v" )
                                                  
                                                  or sensibilidade ==0 ) 
                                            # and (   (( sensibilidade, positivo5, msg_panico5 ) in [ ('alta','^','^')  ] ) 
                                            #      or (sensibilidade =='media' and positivo5 !="v" and msg_panico5 =="^"  ) 
                                            #       or sensibilidade =='baixa' )  
                                              
                                                    
                                              
                                              )
                         
                            # opcoes = ["Baixa" ,"Media", "Alta", "Mega" ,"Ultra" ]
                            condicao_baixa = (tipo_vela.startswith('negativa') 
                                            #and pavio.upper() != "T^"    
                                            and (pavio or '').upper()!= "T^" 
                                            #and positivo5 !="^"
                                            #and msg_panico5 =="v" #testar a consolidacao do sinal
                                            #and (pavio.upper, terceira_letra)in [("LV","g" )("LV","r")]
                                            # and app_direcao=='QUEDA'
                                            #and ep_master.get("expectativa")!='ALTA'  #USANDO AQUI
                                            and expectativaK !='ALTA'
                                            and terceira_letra not in ("G", "g")
                                            and ultima_vela not in ("G", "g")
                                            #and ultima_vela.upper()!="G"
                                            # and impulso not in ["ACELERAÇÃO DE ALTA (RSI se afastando para cima)","APROXIMAÇÃO ACELERADA (RSI subindo em direção à MA)","IMPULSO INDEFINIDO (oscilação sem direção clara)"]
                                            and (recomendacao_kamikazi in kami_baixa) 
                                            and (tipo_opcao.lower(), saida, app_direcao) in [('put', 'compra','ALTA' ), ('call', 'venda', 'QUEDA')]

                                            and (   (( sensibilidade, positivo5, msg_panico5, sentido_posi5, ep_master.get("expectativa"), (ultima_vela or '').upper() ) in [ (4,'v','v','v','QUEDA', 'R')  ]  and "AGUARDAR" not in recomendacao ) or #ultra
                                                 
                                                 (( sensibilidade, positivo5, msg_panico5, sentido_posi5, (ultima_vela or '').upper() ) in [ (3,'v','v','v', 'R')  ]  and "AGUARDAR" not in recomendacao ) #mega
                                                 
                                                 or (sensibilidade ==2 and positivo5 !="^" and msg_panico5 =="v" and sentido_posi5 !="^" and (ultima_vela or '').upper()=='R' ) #alta 
                                                 or (sensibilidade ==1 and positivo5 !="^" and msg_panico5 !="^" and sentido_posi5 !="^" ) #media 
                                                  or sensibilidade ==0 ) #baixa
                                            # and (   (( sensibilidade, positivo5, msg_panico5 ) in [ ('alta','v','v')  ] ) 
                                            #      or (sensibilidade =='media' and positivo5 !="^" and msg_panico5 =="v"  ) 
                                            #       or sensibilidade =='baixa' ) 
                                                 
                                             
                                             
                                             )
                            #print ( f"teste  {ativo} {sensibilidade, positivo5, msg_panico5}" )            
                            
                            if condicao_alta or condicao_baixa:
                                primeiro = saida
                                print(f" {primeiro}KAMIKAZI"*200)
                                break                

                            
    
                    



                    # elif infoObs.get("micro_tende") in ['CAVEIRA_G', 'CAVEIRA_R', 'HULL_R', 'HULL_G', 'CIMA', 'BAIXO']:
                    #     print("todas as saida possiveis", ambas_op, ana_fim4, vcva, status1, melhor_op)
                        
                        
                    #        # valor padrão
                    #     for saida in saidas_possiveis:
                    #         # Garantir que 'saida' não é None (se for, pular)
                    #         if saida is None:
                    #             continue
                    #         condicao_micro_tendencia = (infoObs.get("micro_tende"), tipo_opcao.lower(), saida) in estados_micro_tendencia
                    #         condicao_top = (saida, tipo_opcao.lower(), infoObs.get("seta"), terceira_letra) in melhores_condicoes
                    #         if condicao_micro_tendencia and condicao_top:
                    #             primeiro = saida
                    #             print(saida, " da micro")
                    #             break   # para no primeiro encontrado
                    #     else:
                    #         # Se nenhum match for encontrado
                    #         print("Nenhuma saída válida para a micro tendência")    
                    #         #primeiro='neutro'
                    
                    # elif infoObs.get("micro_tende") not in ['CAVEIRA_G', 'CAVEIRA_R', 'HULL_R', 'HULL_G', 'CIMA', 'BAIXO']  and primeiro==None :
                    #     for saida in saidas_possiveis:
                    #         # Garantir que 'saida' não é None (se for, pular)
                    #         if saida is None:
                    #             continue
                            
                    #         condicao_seta = (saida, tipo_opcao.lower() , infoObs.get("seta"),  terceira_letra) not in estados_seta and terceira_letra != '+'
                    #         condicao_top = (saida, tipo_opcao.lower(), infoObs.get("seta"), terceira_letra) in melhores_condicoes
                    #         if condicao_seta and condicao_top :
                    #             primeiro = saida
                    #             print(saida, " da seta")
                    #             break   # para no primeiro encontrado
                    #     else:
                    #         # Se nenhum match for encontrado
                    #         print("Nenhuma saída válida para a micro tendência")
                    #         primeiro='neutro'


                    
                    #elif ana_fim4 in ['COMPRA', 'VENDA']:
                    #    primeiro = ana_fim4.lower()
                    #    print ( "do ana_fim4",ana_fim4 ,decisao_case, decisao4 )
                    
                    
                    else:
                        primeiro = 'neutro'


                    if primeiro ==None: primeiro='neutro'  

                    print("ants das condicionais", primeiro, caso, recomendacao_kamikazi, recomendacao )    
                    
                    decisao4 = ""#'EVITAR'
                    an_hib_decisao= ""#'EVITAR'
                    
                    
                    if primeiro in ['compra', 'venda']:
                        print(f"PRIMEIRO {primeiro}")    
                        analise_completa4 =  analisar_com_symbolinfo4(
                                        ativo=ativo,
                                        status=primeiro,
                                        resultado_antigo=resultado_antigo,
                                        resultado_novo=resultado_novo,
                                        symbol_info=inform )    
                        
                        decisao4= analise_completa4['decisao_integrada']['decisao']
                        an_hib_decisao=analise_hibrida_completa(ativo, primeiro)["decisao_final"]
                        resultado_antigo = intensidade_sinal_antiga(ativo, primeiro)
                        resultado_novo = intensidade_sinal(ativo, primeiro)
                        analise = sistema.analisar_operacao_completa(ativo, primeiro, resultado_antigo, resultado_novo, inform)
                        fatores_decisivos = analise.get('decisao_integrada', {}).get('fatores_decisivos', [])
                    
                    
                    

                        an_hib_decisao_c=analise_hibrida_completa(ativo, 'compra')["decisao_final"]
                        an_hib_decisao_v=analise_hibrida_completa(ativo, 'venda')["decisao_final"]
                        print ("para compra:", an_hib_decisao_c, "para venda:" , an_hib_decisao_v )
                        
                    
                    #condicao_ideal = (primeiro, tipo_opcao.lower() , infoObs.get("seta")) in [('compra', 'call', 'T^' ), ('venda', 'call', 'LV' ) , ('venda', 'put', 'T^'),  ('compra', 'put', 'LV')    ]                                                                                                                   
                    
                    #TESTATR ESSA MUDANCA  tava OR mudei para AND
                    condicao_adversa_entrar = (tipo, (tipo_op(ativo)).lower() , seta, terceira_letra) not in [
                        ('compra', 'call','LV', 'R'),('compra', 'call',None, 'R'),('compra', 'call','LV', 'r'),('compra', 'call',None, 'r'), 
                        ('venda', 'call' ,'T^','G'), ('venda', 'call' ,'LV','G'),  ('venda', 'call' ,None,'G'),('venda', 'call' ,'T^','g'),('venda', 'call' ,None,'g'), 
                        
                        ('venda', 'put' ,'LV', 'R'), ('venda', 'put',None, 'R'),('venda', 'put','LV', 'r'),('venda', 'put',None, 'r'),
                        
                        ('compra', 'put' ,'T^','G'), ('compra', 'put' ,'LV','G')   ,('compra', 'put' ,None,'G'),('compra', 'put' ,'T^','g'),('compra', 'put' ,None,'g') ] 
                    #print(f"condicao adversa para {ativo} {condicao_adversa}") 
                    
                        
                    

                    condicao_top = (primeiro, tipo_opcao.lower(), infoObs.get("seta"), terceira_letra) in melhores_condicoes
   
                    condicao_seta = (primeiro, tipo_opcao.lower() , infoObs.get("seta"),  terceira_letra) not in estados_seta and terceira_letra != '+'
                    """ condicao_ideal = ( primeiro, tipo_opcao.lower(), infoObs.get("seta") in [
                                                                                                ('compra', 'call', 'T^'),
                                                                                                ('venda', 'call', 'LV'),
                                                                                                ('venda', 'put', 'T^'),
                                                                                                ('compra', 'put', 'LV')
                                                                                            ]
                                                                                        )
 """                
                    # condicao_ideal = ( primeiro, tipo_opcao.lower(), infoObs.get("seta") not in [
                    #                                                                             ('venda', 'call', 'T^'),
                    #                                                                             ('compra', 'call', 'LV'),
                    #                                                                             ('compra', 'put', 'T^'),
                    #                                                                             ('venda', 'put', 'LV')
                    #                                                                         ]
                    #                                                                     )

                    condicao_ideal = ( primeiro, tipo_opcao.lower(), pavio) not in [
                                                                                                ('venda', 'call', 'T^'),
                                                                                                ('compra', 'call', 'LV'),
                                                                                                ('compra', 'put', 'T^'),
                                                                                                ('venda', 'put', 'LV')
                                                                                            ]
                                                                                        

                    
                    
                    condicao_final = (
                                        (primeiro, tipo_opcao.lower(), infoObs.get("seta"), terceira_letra) not in estados_seta
                                        and terceira_letra != '+'
                                        and (primeiro, tipo_opcao.lower(), pavio) not in [
                                            ('venda', 'call', 'T^'),
                                            ('compra', 'call', 'LV'),
                                            ('compra', 'put', 'T^'),
                                            ('venda', 'put', 'LV')
                                        ]
                                    )

                    

                    
                    
                    """ condicao_ideal = (
                                   (dados['status'] == ana_fim4.lower() )
                                    and (primeiro, tipo_opcao.lower(), infoObs.get("seta")) in [
                                                                                                ('compra', 'call', 'T^'),
                                                                                                ('venda', 'call', 'LV'),
                                                                                                ('venda', 'put', 'T^'),
                                                                                                ('compra', 'put', 'LV')
                                                                                            ]
                    
                                                                                        )
 """
                    #Aqui é a parte final de decisao:   ('VALED864', 'compra', 'LV', 'rRg(LV)', 'COMPRA', 'AGUARDAR_CONFIRMAÇÃO') ideal True seta True,  Analise hibrida: AGUARDAR LV status compra  status1:compra
                    mensagem_intensidade, percentual, perc_principal = intensidade_sinal(ativo, primeiro)                                  
                    mensagem_intensidade_a, percentual_a, perc_principal_a = intensidade_sinal_antiga(ativo, primeiro)
                    intensao = sentimento_msg(INTENSAO, mensagem_intensidade)    
                     
                    
                    #dados["intensidade"] = f"{percentual} {ep_expectativa}" #if abs(diff) >= GATILHO_DIFF_PRECO else 0.0 #status
                    #dados["int_geral"] = f"{perc_principal} ", ep_master.get("expectativa") #if abs(diff) >= GATILHO_DIFF_PRECO else 0.0 #vcv

                     



                    #print(vcv['decisao'], vcva, decisao_case ,vcv['tamanho_posicao'] , vcv['detalhes'] ,vcv['detalhes']['direcao_tendencia'])
                    
                    
                    print ("ate aqui sem erro4")
                    
                    if ( f"{primeiro.upper()} FORTE" in mensagem_intensidade):
                        await enviar_telegram( f"{primeiro.upper()} FORTE"  )
                        try:
                            winsound.Beep(800, 500)
                        except:
                            pass
   
                    
                                  



                    print (  f"Aqui é a parte final de decisao:   {ativo,  ALERTA_ATUAL, bracket, ana_fim4, decisao4} final{primeiro} ideal { primeiro, tipo_opcao,seta ,condicao_ideal, condicao_adversa_entrar } seta {condicao_seta },  Analise hibrida:",an_hib_decisao ,  infoObs.get("seta"),
                           "status",dados["status"],f" status1:{status1}","\n fatores:", fatores_decisivos," gap: ",
                            gap," DIF:" ,abs(diff)," >= " ,GATILHO_DIFF_PRECO , '\n', gap,"<=",0.03,  "decisao4", decisao4,"....")
                    
                    apuracao=f"resultado para entrar {an_hib_decisao} , status1: {status1} ,vcv:   ", dados["status"] 
                    mensagem = (f"🔎 {ativo} mudou de status!\n" f"Inicial: {dados['preco_inicial']:.2f} | Atual: {preco:.2f}\n"f"➡️ Sinal sugerido: {mensagem_intensidade} \n apuracao: {apuracao}")                                          
                                                                                                                     

                    #colocado a condicao ideal como fator decisivo
                    

                    





                    #original if dados["status"] in ["venda", "compra"] and condicao_ideal and condicao_seta and condicao_caveira and dentro_horario() and gap <=GATILHO_DIFF_PRECO+0.015  \
                    #      and  decisao4 not in['BLOQUEAR','EVITAR'] and AUTOMATIZAR and caso!="" and dados["intensidade"] >= LIMIAR_FORCA: #and gap_preco_real(ativo)< 2 : #and ativo.upper()[:4] == ATIVO_COM_ALERTA and (ALERTA_ATUAL=="HULL" or ALERTA_ATUAL=="CAVEIRA" or ALERTA_ATUAL=="CAVEIRA_P*"):
                    #if an_hib_decisao in["EXECUTAR_ORDEM","AGUARDAR" ,"EXECUTAR_COM_CUIDADO"] and dados["status"] in ["venda", "compra"] and dentro_horario() and AUTOMATIZAR : #and gap_preco_real(ativo)< 2 : #and ativo.upper()[:4] == ATIVO_COM_ALERTA and (ALERTA_ATUAL=="HULL" or ALERTA_ATUAL=="CAVEIRA" or ALERTA_ATUAL=="CAVEIRA_P*"):
                    # Calcula o primeiro gatilho
                    
#SE NA INFLUENCIA DE UM SINAL MUDAR PARA ACEITAR TUDO QUE FOR RELATIVO AO SINAL
                    
                    # Condição completa (use os parênteses no or, como discutimos antes)
                    #print("Algum false ou bloquaer ", primeiro,ambas_op ,condicao_ideal, condicao_seta, condicao_adversa_entrar  ,condicao_caveira, gap, decisao4, an_hib_decisao,mensagem_ambas ,dados["intensidade"], ">=" ,LIMIAR_FORCA )
                    
                    
                    decisoes_dict = {
                                        'ativo': ativo,
                                        "primeiro": primeiro,
                                        "ambas_op": ambas_op,
                                        #"condicao_ideal": condicao_ideal,
                                        #"condicao_seta": condicao_seta,
                                        #"condicao_adversa_entrar": condicao_adversa_entrar,
                                        #"condicao_caveira": condicao_caveira,
                                        #"condicao_top": condicao_top,
                                        #"condicao_ideal": condicao_ideal,
                                        #"condicao_final":     condicao_final,
                                        #"gap": gap,
                                        #"decisao4": decisao4,
                                        #"an_hib_decisao": an_hib_decisao,
                                        #"mensagem_ambas": mensagem_ambas,                                        
                                        "recomndacao kamikazi": recomendacao_kamikazi,
                                        "recomndacao ": recomendacao,
                                        "Acho kamikazi ": acho,
                                        "ultima vela": tipo_vela,
                                        #"gap_venda:": gap_v,
                                        "SETA ": seta,
                                        "SETA DO RSI": pavio,
                                        #"lateral:": lateral, 
                                        #"rompeu": rompeu,
                                        "ultima_letra ": ultima_vela,
                                        "terceira_letra ": terceira_letra,
                                        "direcao_rsi:": direcao_rsi, 
                                        "APP_DIRECAO: " : app_direcao,
                                        "APP_FORCA: "  : app_forca,
                                        "impulso:": impulso,           
                                        "intensao" : intensao,
                                        "positivo5": positivo5,
                                         "msg_panico": msg_panico5,
                                         #"sinal_f_nova":sinal_op_30.get("sinal"),
                                         #"motivo":sinal_op_30.get("motivo"),
                                         #"sinal_f_nova_m":sinal_op_30_m.get("sinal"),
                                         # "motivo_m":sinal_op_30_m.get("motivo"),

                                         
                                         }
                    
                    # resultado = rompimento_saida(ativo, n=1, timeframe=5)
                    # if resultado is not None:
                    #     rompeu = resultado[2]   # terceiro elemento
                    #     msg_panico = resultado[3]
                    #     print(f"{rompeu},  {msg_panico}")    

                    print("$"*100)
                    
                    print(saidas_possiveis)
                    
                    #print ( f"{tipo_vela, pavio, recomendacao_kamikazi, tipo_opcao, impulso}"  )
                                        


                    for nome, valor in decisoes_dict.items():
                        print(f"{nome}: {valor}")
                    
                    print (f"ultra{sensibilidade, positivo5, msg_panico5, sentido_posi5, (ultima_vela or '').upper() }", ep_master.get("expectativa"))
                    print (f"mega {sensibilidade, positivo5, msg_panico5, sentido_posi5, (ultima_vela or '').upper()  }")
                    print(recomendacao_kamikazi, gap ,pavio ,sensibilidade, positivo5, msg_panico5, sentido_posi5, ep_master.get("expectativa"), (ultima_vela or '').upper() )    
                    print(f"o resultado de entrada da ia", resultado['sinal'], resultado['confianca'] )
                    
                    if ( gap >GATILHO_DIFF_PRECO): print (f"O GAP ESTA ALTO {gap}")          
                    if "contra" in mensagem:
                        inicio = mensagem.find("contra") + len("contra")
                        pedaco = mensagem[inicio:inicio + 10]
                        print(f"Após 'contra': '{pedaco}'")
                                        
                    if recomendacao_kamikazi in kami_baixa:
                        match sensibilidade:
                            case 4:
                                esperados = {
                                    "positivo5": "v",
                                    "msg_panico5": "v",
                                    "sentido_posi5": "v",
                                    "expectativa": "QUEDA",
                                    "ultima_vela":'R'
                                }
                                reais = {
                                    "positivo5": positivo5,
                                    "msg_panico5": msg_panico5,
                                    "sentido_posi5": sentido_posi5,
                                    "expectativa": ep_master.get("expectativa"),
                                    "ultima_vela":(ultima_vela or '').upper()
                                }
                                falhos = [nome for nome, val_esp in esperados.items() if reais[nome] != val_esp]
                                if falhos:
                                    print(f"Fatores fora do esperado: {falhos}")
                            case 3:
                                esperados = {
                                    "positivo5": "v",
                                    "msg_panico5": "v",
                                    "sentido_posi5": "v",                                    
                                    "ultima_vela":'R'
                                }
                                reais = {
                                    "positivo5": positivo5,
                                    "msg_panico5": msg_panico5,
                                    "sentido_posi5": sentido_posi5,                                    
                                    "ultima_vela":(ultima_vela or '').upper()
                                }
                                falhos = [nome for nome, val_esp in esperados.items() if reais[nome] != val_esp]
                                if falhos:
                                    print(f"Fatores fora do esperado: {falhos}")
                            
                            case 2: 
                                
                                esperados = {                                                                      
                                    "msg_panico5": "v",
                                    "ultima_vela":'R'
                                }
                                reais = {
                                    "msg_panico5": msg_panico5,                                                                        
                                    "ultima_vela":(ultima_vela or '').upper()
                                }
                                falhos = [nome for nome, val_esp in esperados.items() if reais[nome] != val_esp]
                                if positivo5!='v' or  sentido_posi5!='v': falhos+=f"positivo5 {positivo5}, sentido_posi5 {sentido_posi5}"                              
                                
                                if falhos:
                                    print(f"Fatores fora do esperado: {falhos}")
                            case 1:
                                if positivo5 !="^" or msg_panico5 !="^" or sentido_posi5 !="^":
                                   print (f"positivo5 {positivo5}, sentido_posi5 {sentido_posi5}, msg_panico{msg_panico5}") 
                            case _: 
                                print("outros fatores")
                    elif recomendacao_kamikazi in kami_alta:
                        match sensibilidade:
                            case 4:
                                esperados = {
                                    "positivo5": "^",
                                    "msg_panico5": "^",
                                    "sentido_posi5": "^",
                                    "expectativa": "ALTA",
                                    "ultima_vela":'G'
                                }
                                reais = {
                                    "positivo5": positivo5,
                                    "msg_panico5": msg_panico5,
                                    "sentido_posi5": sentido_posi5,
                                    "expectativa": ep_master.get("expectativa"),
                                    "ultima_vela":(ultima_vela or '').upper()
                                }
                                falhos = [nome for nome, val_esp in esperados.items() if reais[nome] != val_esp]
                                if falhos:
                                    print(f"Fatores fora do esperado: {falhos}")
                            case 3:
                                esperados = {
                                    "positivo5": "^",
                                    "msg_panico5": "^",
                                    "sentido_posi5": "^",                                    
                                    "ultima_vela":'G'
                                }
                                reais = {
                                    "positivo5": positivo5,
                                    "msg_panico5": msg_panico5,
                                    "sentido_posi5": sentido_posi5,                                    
                                    "ultima_vela":(ultima_vela or '').upper()
                                }
                                falhos = [nome for nome, val_esp in esperados.items() if reais[nome] != val_esp]
                                if falhos:
                                    print(f"Fatores fora do esperado: {falhos}")
                            
                            case 2: 
                                
                                esperados = {                                                                      
                                    "msg_panico5": "^",
                                    "ultima_vela":'G'
                                }
                                reais = {
                                    "msg_panico5": msg_panico5,                                                                        
                                    "ultima_vela":(ultima_vela or '').upper()
                                }
                                falhos = [nome for nome, val_esp in esperados.items() if reais[nome] != val_esp]
                                if positivo5!='^' or  sentido_posi5!='^': falhos+=f"positivo5 {positivo5}, sentido_posi5 {sentido_posi5}"                              
                                
                                if falhos:
                                    print(f"Fatores fora do esperado: {falhos}")
                            case 1:
                                if positivo5 !="v" or msg_panico5 !="v" or sentido_posi5 !="v":
                                   print (f"positivo5 {positivo5}, sentido_posi5 {sentido_posi5}, msg_panico{msg_panico5}") 
                            case _: 
                                print("outros fatores")
                        

                    

                    print("-"*100)
                    print("$"*100)
                    
                                                                    
                                
                    
                    #if acho and  : print ("VAI SUBIR ESSA MERDA") 
                    #CONDICAO_ACHO = (acho, status1, tipo_opcao.lower() ) in [('up', 'venda', 'put'), ('up', 'compra', 'call'), ('down', 'venda', 'call'), ('down', 'compra', 'put')    ]
                    #CONDICAO_ACHO = (acho, primeiro, tipo_opcao.lower()) in [('up', 'venda', 'put'), ('up', 'compra', 'call'), ('down', 'venda', 'call'), ('down', 'compra', 'put')] and "AGUARDAR" not in recomendacao_kamikazi


                    CONDICAO_ACHO = ( direcao_rsi , acho, primeiro, tipo_opcao.lower()) in [('vai subir',  'up', 'venda', 'put'), ('vai subir','up', 'compra', 'call'), 
                                                                                            ("vai descer",'down', 'venda', 'call'), ("vai descer",'down', 'compra', 'put')] and "AGUARDAR" not in recomendacao_kamikazi
                    
                    
                    CONDICAO_kamikazi = ( direcao_rsi ,  primeiro, tipo_opcao.lower()) in [('vai subir',   'venda', 'put'), ('vai subir', 'compra', 'call'), 
                                                                                            ("vai descer", 'venda', 'call'), ("vai descer", 'compra', 'put')] and "AGUARDAR" not in recomendacao_kamikazi
                    
                    #condicao_direcao_rsi= ( direcao_rsi, primeiro, tipo_opcao.lower()) in [( "vai subir", 'venda', 'put'   ) , ("vai subir",'compra', 'call') ,  ("vai decer", 'compra', 'put' )  ("vai decer", 'venda', 'call' )  ]

                    
                    print("$"*100)
                    print (ativo_principal(ativo),ep_master.get("expectativa"), ep_master.get ("intensidade"))
                    print(f"ESTRATEGIA DA POUCA condicao kamikazi{CONDICAO_kamikazi} {ativo} {gap} { primeiro} tipo de opcao {tipo_opcao} condicao acho {CONDICAO_ACHO}( { direcao_rsi, acho, primeiro ,tipo_opcao}   )"    )
                    print("$"*100)
                    
                    #ESTRATEGIA DA POUCA condicao_rsi vai descer VALEQ819 compra tipo de opcao PUT condicao acho False( ('vai descer', 'down', 'compra', 'PUT')   )

                    #print(f"condicao acho {CONDICAO_ACHO}")
                    pode_entrar_k = UMA_OPCAO_P_LETRA_por_ROBO and (total_entradas < 2) and (contagens['kami'] == 0    )
                    
                    dados["status"] = primeiro, ep_expectativa,acho ,condicao_top,seta #, terceira_letra,condicao_adversa_entrar, condicao_final
                    
                    
                    if (primeiro is not None and primeiro in ['compra', 'venda']

                        and pode_entrar_k    
        #O GAP DA OPCAO NÃO PODE SER MAIOR QUE 0.02                
                        #and CONDICAO_ACHO
                        #modo KAMIKAZI
                        # and condicao_ideal
                        # and condicao_seta
                        # and condicao_caveira
                        # and condicao_top
                        # and rompeu    #testar saida de lateralizacao
                        #and gap<0.02   # 
                        and app_direcao != "NEUTRO"
                        and "AGUARDAR" not in recomendacao_kamikazi
                        #and "AGUARDAR" not in recomendacao
                        #and condicao_adversa_entrar
                        and intensao
                        and gap <= max(GATILHO_DIFF_PRECO, 0.02)
                        #and gap <  GATILHO_DIFF_PRECO #+ 0.015
                        #and decisao4 not in ESTRATEGIAS_ruins    #['BLOQUEAR', 'EVITAR']
                        #and an_hib_decisao not in ESTRATEGIAS_ruins
                        and AUTOMATIZAR                        
                        #and dados["intensidade"] >= LIMIAR_FORCA  
                        and dentro_horario() )   :
                        
                        dados["status"] = primeiro   # agora corresponde ao primeiro que liberou
                        # resto da lógica
                        
                        print (  f"OPERACAO REALIZADA:   {ativo, primeiro, ambas_op ,ALERTA_ATUAL, bracket, ana_fim4, decisao4} /n final{primeiro} adversas{condicao_adversa_entrar}  ideal { primeiro, tipo_opcao,seta ,condicao_ideal} seta {condicao_seta },  Analise hibrida:",an_hib_decisao ,  infoObs.get("seta"),
                           "status",dados["status"],f" status1:{status1}","\n fatores:", fatores_decisivos," gap: ",
                            gap," DIF:" ,abs(diff)," >= " ,GATILHO_DIFF_PRECO , '\n', gap,"<=",0.03,  "decisao4", decisao4,"....")
                    
                    
                        print(f"condicao ideal {condicao_ideal}")
                        print(f"condicao seta {condicao_seta}")
                        print(f"condicao caveira {condicao_caveira}")
                        print(f"condicao adversa {condicao_adversa_entrar}")
                    
                    
                    
                        try:
                            winsound.Beep(2000, 700)  # beep diferenciado para mini stop
                        except:
                            pass
                        
                        print('PASSOU AQUI '*10, decisao4)
                        NOVA_MSG = dados['status'],f"a condicao de seta: {condicao_seta} e caveira {condicao_caveira} ideal{condicao_ideal} vela atual{terceira_letra} para o ativo {ativo}  {tipo_opcao} Status: ", infoObs.get("status"),"seta: " ,infoObs.get("seta"), infoObs.get("bracket") 
         
                        status= dados["status"]
                        pr=preco_real(ativo, status)

                        stop_loss_pct=     STOP_LOSS_PADRAO   
                        if status == "compra":
                            stop_loss_valor = preco * (1 - stop_loss_pct/100.0)
                        else:  # venda
                            stop_loss_valor = preco * (1 + stop_loss_pct/100.0)
                            
                        #verificar por tamanho da posicao
                        
                        #especial= True if vcv["decisao"]==status1 else False
                        #qtd_extra=0
                        #qtd_extra = QTD_ESPECIAL if especial and an_hib_decisao=="EXECUTAR_ORDEM" else 0
                        
                        
                        #if especial and an_hib_decisao=="EXECUTAR_ORDEM": qtd_extra= QTD_ESPECIAL
                        #QTD_AUTO=QTD_AUTO+qtd_extra
                        








                        
                        print("*"*60)
                        print("Verificar antees de entrar: " ,ALERTA_ATUAL , ATIVO_COM_ALERTA, caso, gap_preco_real(ativo), an_hib_decisao )

                        print ( status ,gap ,  an_hib_decisao, caso ,dados["intensidade"] )#and gap_preco_real(ativo)< 2 : #and ativo.upper()[:4] == ATIVO_COM_ALERTA and (ALERTA_ATUAL=="HULL" or ALERTA_ATUAL=="CAVEIRA" or ALERTA_ATUAL=="CAVEIRA_P*"):
                        print("*"*60)
                        bk_deci4=""
                        if "AGUARDAR" not in recomendacao_kamikazi and decisao4 in ESTRATEGIAS_ruins    : 
                            bk_deci4=decisao4
                            decisao4="kamikazi"

                        if decisao4 not in ESTRATEGIAS_ruins  : #an_hib_decisao not in ESTRATEGIAS_ruins:

                            
                            ATIVOS[ativo] = {
                                "qtd": QTD_AUTO,
                                "entrada": pr,
                                "tipo": status,
                                "stop_loss_pct": STOP_LOSS_PADRAO,
                                "stop_loss_valor": stop_loss_valor,
                                "ultimo_status": None,
                                "max_diff": 0.0,
                                "mini_stop_pct": IDENTIFICADOR_ROBO,
                                "mute": False,
                                "intensidade": 10,
                                "ia_resultado": "entrada_kami", #resultado,      # <-- Guarda a decisão (sinal, confiança)
                                "ia_estado": estado_str #estado_ia          # <-- ✅ GUARDA O ESTADO COMPLETO!
                            }
                            
                            
                            
                        #     ATIVOS[ativo] = {"qtd": QTD_AUTO, "entrada": pr, "tipo": status, "stop_loss_pct": STOP_LOSS_PADRAO,
                        # "stop_loss_valor": stop_loss_valor,
                        #             "ultimo_status": None, "max_diff": 0.0,
                        # "mini_stop_pct": IDENTIFICADOR_ROBO, "mute": False, "intensidade":percentual, "historico": f"{decisao4, bk_deci4, impulso, status1, pavio} {rompeu} {msg_panico5} {rompeu5} {CONDICAO_ACHO} {condicao_top} {CONDICAO_kamikazi} {condicao_ideal} {condicao_seta} {app_direcao} {app_forca} {ep_expectativa} {ep_intensidade}{pavio} {terceira_letra} {ultima_vela}"+f"{gap:.2f}" }  #an_hib_decisao+status1+caso
                            
                            enviar_ordem(ativo, status, QTD_AUTO, "1")
                            
                            await enviar_telegram(f"✅ ROBO AQUI 🤖 {status.capitalize()} registrada: {ativo} | Entrada: {preco_real(ativo, status)} | Qtd: {QTD_AUTO} | gap:{gap:.2f} | {mensagem_intensidade} | {mensagem}", "")

                            print ("sera quw o  errro aqui 2")

                            print(mensagem_intensidade)
                            print ("sera quw o  errro aqui 3")
                            # ver = {
                            #         "ativo":ativo,                                    
                            #         "decisao4": decisao4,
                            #         "rompeu": rompeu,
                            #         "CONDICAO_ACHO": CONDICAO_ACHO,
                            #         "condicao_top": condicao_top,
                            #         "CONDICAO_kamikazi": CONDICAO_kamikazi,
                            #         "condicao_ideal": condicao_ideal,
                            #         "condicao_seta": condicao_seta,
                            #         "app_direcao": app_direcao,
                            #         "app_forca": app_forca,
                            #         "pavio": pavio,
                            #         "terceira_letra": terceira_letra,
                            #         "ultima_velaRSI": ultima_vela
                            #     }
                            # print ("sera quw o  errro aqui 4")
                            # with open("meu.txt", "w", encoding="utf-8") as f:
                            #     json.dump(ver, f, indent=4, ensure_ascii=False)


                            
                            #print(type(vcv))
                            print("decisao final:", status, vcv["decisao"] )
                                                        
                            dados["intensidade"]= primeiro,CONDICAO_ACHO,condicao_top,condicao_final ,seta, terceira_letra,condicao_adversa_entrar
                            
                            
                           
                            salvar_ativos()
                            
                    #--------------------------------------------------------    


                    
                    
                        
                    
                    
                    else: 
                        # Calcula o que deve ser exibido para cada campo
                        gap_display = "" if gap <= GATILHO_DIFF_PRECO + 0.015 else gap
                        
                        # mudei aqui intens_display = "" if dados["intensidade"] >= LIMIAR_FORCA else dados["intensidade"]
                        intens_display = ep_expectativa
                        # Se quiser também filtrar outros campos, faça o mesmo

                        NOVA_MSG = (
                            f"{ativo} operacao: {dados['status']} "
                            f"condicao ideal {condicao_ideal} decis4: {decisao4} "
                            f"condicao_seta: {condicao_seta} caveira: {condicao_caveira} "
                            f"gap: {gap_display} | intens: {intens_display} | "
                            f"anafim: {ana_fim4} status1: {status1}"
                        )
                        
                    
                        await enviar_telegram(f"⚠️ Sinal {status.upper()} ignorado para {ativo} (movimento abaixo do limiar {LIMIAR_FORCA}%)\n{mensagem_intensidade}"
    )
                
                
                        #await enviar_telegram(mensagem)
                        #await enviar_telegram(f"🔎 {ativo} agora sugere {status.upper()} | Inicial: {dados['preco_inicial']:.2f} | Atual: {preco:.2f}")
        #except Exception as e:
        #    print("⚠️ Erro no monitoramento:", e)
        except Exception as e:
            
            if 'NoneType' in str(e):
                   
                print(f"erro de NONE {ativo}"*200)
                traceback.print_exc()
                pass
            
            elif 'classificacao_book' in str(e):
                #dados["reset"]=1
                #dados["preco_inicial"]=preco_medio(ativo)



                resposta=(f"Problemas na funcao {ativo} {preco} {tipo_opcao} {status1}  {decisao4} fim {ana_fim4}")
                print(resposta*200)
                await enviar_telegram(resposta)

                pass   # ignora esse erro específico
            else:
                print("⚠️ Erro no monitoramento monitoriar ativos:", e)    

        await asyncio.sleep(10)           

# --- Envia arquivos MT5 ---
async def enviar_arquivos_mt5():
    global ULTIMA_IMAGEM, ULTIMA_IMAGEM_NOME, filtro_imagem_ativo_carteira 
    foto_filtrada=False
    while True:
        try:
            # Mensagens texto
            if os.path.exists(TEXT_PATH):
                if MOSTRAR_MSGS:
                    if FILTRAR_MENSAGEM:                    
                        mensagens = filtrar_mensagens_textpath()
                        for msg in mensagens:                    
                            await enviar_telegram(f"📩 Mensagem filtrada: {msg}")
                
                    else:
                        with open(TEXT_PATH, "r", encoding="utf-8") as f:
                            texto = f.read()
                            await enviar_telegram(texto)
                                
                os.remove(TEXT_PATH)

            # Screenshots/imagens
            if os.path.isdir(PATH):
                for nome_do_arquivo in os.listdir(PATH):
                    if nome_do_arquivo.lower().endswith((".png", ".jpg", ".jpeg")):
                        caminho = os.path.join(PATH, nome_do_arquivo)
                        if os.path.exists(caminho):
                            # envia ao Telegram
                            
                            if MOSTRAR_FOTOS:
                                if MOSTRAR_FOTOS_CARTEIRA:
                                    for ativo in ATIVOS.keys():
                                        prefixo = ativo.upper()[:4]
                                        if prefixo in nome_do_arquivo:
                                            await enviar_telegram(nome_do_arquivo, caminho)
                                            shutil.copy(caminho, ULTIMA_IMAGEM)
                                            ULTIMA_IMAGEM_NOME = nome_do_arquivo
                                        
                                        break
                                else:
                                    await enviar_telegram(nome_do_arquivo, caminho)
                                    # copia para arquivo fixo e guarda o nome original para a legenda
                                    shutil.copy(caminho, ULTIMA_IMAGEM)
                                    ULTIMA_IMAGEM_NOME = nome_do_arquivo                             
                            #if MOSTRAR_FOTOS and foto_filtrada:
                            #    await enviar_telegram(nome_do_arquivo, caminho)
                            # copia para arquivo fixo e guarda o nome original para a legenda
                            #shutil.copy(caminho, ULTIMA_IMAGEM)
                            #ULTIMA_IMAGEM_NOME = nome_do_arquivo
                            
                            # remove a origem (limpeza da pasta do MT5)
                            os.remove(caminho)
        except Exception as e:
            print("⚠️ Erro ao enviar arquivos MT5:", e)

        await asyncio.sleep(5)

# --- GUI Tkinter ---
def iniciar_gui():
    #global MOSTRAR_MSGS, MOSTRAR_FOTOS, MOSTRAR_PYTHON, FILTRAR_MENSAGEM,MOSTRAR_FOTOS_CARTEIRA, SOM,APENAS_MSGS_STOP, NOVA_MSG,tree_finalizados,ANALISE_ESTRATEGIA
    global MOSTRAR_MSGS, MOSTRAR_FOTOS, MOSTRAR_PYTHON, FILTRAR_MENSAGEM,MOSTRAR_FOTOS_CARTEIRA, SOM,APENAS_MSGS_STOP, NOVA_MSG,tree_finalizados,ANALISE_ESTRATEGIA 
    
    root = tk.Tk()
    root.title("📊 Dashboard MT5 - Monitor de Ativos")
    root.geometry("1100x850")

    config_vars = {}
    
    def abrir_janela_config():
        """Abre janela de configurações com abas organizadas"""
        config_window = tk.Toplevel(root)
        config_window.title("Configurações do Sistema")
        config_window.geometry("800x500")#800x700
        
        # Frame principal
        main_frame = tk.Frame(config_window)
        main_frame.pack(fill='both', expand=False)
        # Notebook para abas
        frame_test = tk.Frame(main_frame)
        img_label2 = tk.Label(frame_test, text="Última imagem recebida aparecerá aqui", bg="lightgray")
        img_label2.pack()    
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # ===== ABA 1: Telegram e Paths =====
        frame_telegram = ttk.Frame(notebook)
        notebook.add(frame_telegram, text="Telegram & Paths")
        
        # Telegram
        tk.Label(frame_telegram, text="Configurações Telegram", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)
        
        tk.Label(frame_telegram, text="TOKEN:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        token_var = tk.StringVar(value=TOKEN)
        tk.Entry(frame_telegram, textvariable=token_var, width=50).grid(row=1, column=1, padx=5, pady=2)
        config_vars['TOKEN'] = token_var
        
        tk.Label(frame_telegram, text="CHAT_ID_DEFAULT:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        chat_var = tk.StringVar(value=CHAT_ID_DEFAULT)
        tk.Entry(frame_telegram, textvariable=chat_var, width=50).grid(row=2, column=1, padx=5, pady=2)
        config_vars['CHAT_ID_DEFAULT'] = chat_var
        
        tk.Label(frame_telegram, text="Paths", font=('Arial', 12, 'bold')).grid(row=3, column=0, columnspan=2, pady=5)
        
        tk.Label(frame_telegram, text="TEXT_PATH:").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        text_path_var = tk.StringVar(value=TEXT_PATH)
        tk.Entry(frame_telegram, textvariable=text_path_var, width=50).grid(row=4, column=1, padx=5, pady=2)
        config_vars['TEXT_PATH'] = text_path_var
        
        tk.Label(frame_telegram, text="PATH:").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        path_var = tk.StringVar(value=PATH)
        tk.Entry(frame_telegram, textvariable=path_var, width=50).grid(row=5, column=1, padx=5, pady=2)
        config_vars['PATH'] = path_var
        
        tk.Label(frame_telegram, text="TEXT_ATIVAS:").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        text_ativas_var = tk.StringVar(value=TEXT_ATIVAS)
        tk.Entry(frame_telegram, textvariable=text_ativas_var, width=50).grid(row=6, column=1, padx=5, pady=2)
        config_vars['TEXT_ATIVAS'] = text_ativas_var
        
        tk.Label(frame_telegram, text="ATIVOS_PATH:").grid(row=7, column=0, sticky='w', padx=5, pady=2)
        ativos_path_var = tk.StringVar(value=ATIVOS_PATH)
        tk.Entry(frame_telegram, textvariable=ativos_path_var, width=50).grid(row=7, column=1, padx=5, pady=2)
        config_vars['ATIVOS_PATH'] = ativos_path_var
        
        tk.Label(frame_telegram, text="ATIVOS_FINALIZADOS_PATH:").grid(row=8, column=0, sticky='w', padx=5, pady=2)
        finalizados_path_var = tk.StringVar(value=ATIVOS_FINALIZADOS_PATH)
        tk.Entry(frame_telegram, textvariable=finalizados_path_var, width=50).grid(row=8, column=1, padx=5, pady=2)
        config_vars['ATIVOS_FINALIZADOS_PATH'] = finalizados_path_var
        
        # ===== ABA 2: Horários e Preços =====
        frame_horarios = ttk.Frame(notebook)
        notebook.add(frame_horarios, text="Horários & Preços")
        
        # Horários
        tk.Label(frame_horarios, text="Horários de Funcionamento", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)
        
        tk.Label(frame_horarios, text="HORARIO_INICIO (HH:MM):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        inicio_hh = HORARIO_INICIO.hour
        inicio_mm = HORARIO_INICIO.minute
        inicio_hh_var = tk.StringVar(value=str(inicio_hh))
        inicio_mm_var = tk.StringVar(value=str(inicio_mm))
        frm_inicio = tk.Frame(frame_horarios)
        frm_inicio.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        #tk.Entry(frm_inicio, textvariable=inicio_hh_var, width=3).pack(side='left')
        #tk.Label(frm_inicio, text=":").pack(side='left')
        #tk.Entry(frm_inicio, textvariable=inicio_mm_var, width=3).pack(side='left')
        tk.Label(frame_horarios, text="Início:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        frm_inicio = tk.Frame(frame_horarios)
        frm_inicio.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        tk.Spinbox(frm_inicio, textvariable=inicio_hh_var, from_=0, to=23, increment=1, width=3).pack(side='left')
        tk.Label(frm_inicio, text=":").pack(side='left')
        tk.Spinbox(frm_inicio, textvariable=inicio_mm_var, from_=0, to=59, increment=1, width=3).pack(side='left')
        config_vars['HORARIO_INICIO_HH'] = inicio_hh_var
        config_vars['HORARIO_INICIO_MM'] = inicio_mm_var
        






        tk.Label(frame_horarios, text="HORARIO_FIM (HH:MM):").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        fim_hh = HORARIO_FIM.hour
        fim_mm = HORARIO_FIM.minute
        fim_hh_var = tk.StringVar(value=str(fim_hh))
        fim_mm_var = tk.StringVar(value=str(fim_mm))
        frm_fim = tk.Frame(frame_horarios)
        frm_fim.grid(row=2, column=1, sticky='w', padx=5, pady=2)
        #tk.Entry(frm_fim, textvariable=fim_hh_var, width=3).pack(side='left')
        #tk.Label(frm_fim, text=":").pack(side='left')
        #tk.Entry(frm_fim, textvariable=fim_mm_var, width=3).pack(side='left')
        tk.Label(frame_horarios, text="Fim:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        frm_fim = tk.Frame(frame_horarios)
        frm_fim.grid(row=2, column=1, sticky='w', padx=5, pady=2)

        tk.Spinbox(frm_fim, textvariable=fim_hh_var, from_=0, to=23, increment=1, width=3).pack(side='left')
        tk.Label(frm_fim, text=":").pack(side='left')
        tk.Spinbox(frm_fim, textvariable=fim_mm_var, from_=0, to=59, increment=1, width=3).pack(side='left')

        
        
        
        config_vars['HORARIO_FIM_HH'] = fim_hh_var
        config_vars['HORARIO_FIM_MM'] = fim_mm_var
        
        




        # Preços
        tk.Label(frame_horarios, text="Limites de Preço", font=('Arial', 12, 'bold')).grid(row=3, column=0, columnspan=2, pady=5)
        
        tk.Label(frame_horarios, text="MENOR_PRECO_ACEITO:").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        menor_preco_var = tk.DoubleVar(value=MENOR_PRECO_ACEITO)
        tk.Entry(frame_horarios, textvariable=menor_preco_var, width=10).grid(row=4, column=1, sticky='w', padx=5, pady=2)
        config_vars['MENOR_PRECO_ACEITO'] = menor_preco_var
        
        tk.Label(frame_horarios, text="MAIOR_PRECO_ACEITO:").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        maior_preco_var = tk.DoubleVar(value=MAIOR_PRECO_ACEITO)
        tk.Entry(frame_horarios, textvariable=maior_preco_var, width=10).grid(row=5, column=1, sticky='w', padx=5, pady=2)
        config_vars['MAIOR_PRECO_ACEITO'] = maior_preco_var
        
        # tk.Label(frame_horarios, text="INTENSAO:").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        # intensao_var = tk.DoubleVar(value=INTENSAO)
        # tk.Entry(frame_horarios, textvariable=intensao_var, width=10).grid(row=6, column=1, sticky='w', padx=5, pady=2)
        # config_vars['INTENSAO'] = intensao_var

        # tk.Label(frame_horarios, text="INTENSAO:").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        # intensao_var = tk.IntVar(value=INTENSAO)  # valor padrão, pode ser 0,1 ou 2
        # combo = ttk.Combobox(frame_horarios, textvariable=intensao_var, values=[0, 1, 2], width=8, state="readonly")
        # combo.grid(row=6, column=1, sticky='w', padx=5, pady=2)
        # config_vars['INTENSAO'] = intensao_var

        # tk.Label(frame_horarios, text="INTENSAO:").grid(row=6, column=0, sticky='w', padx=5, pady=2)

        # opcoes = ["0 - Todos", "1 - Fraco", "2 - Forte"]
        # combo_intensao = ttk.Combobox(frame_horarios, values=opcoes, state="readonly", width=15)
        # combo_intensao.grid(row=6, column=1, sticky='w', padx=5, pady=2)
        # combo_intensao.current(0)  # Seleciona "0 - Todos" por padrão
        # combo.current(intensao_var.get()) 
        # # Armazena a referência do combo (ou o valor numérico quando necessário)
        # config_vars['INTENSAO'] = combo_intensao  # Agora config_vars guarda o widget


        

        tk.Label(frame_horarios, text="INTENSAO (compradores/vendedores):").grid(row=6, column=0, sticky='w', padx=5, pady=2)

        # Mantém o IntVar com o valor salvo (0,1,2)
        intensao_var = tk.IntVar(value=INTENSAO)  

        # Combobox com textos descritivos (sem textvariable)
       
        
        opcoes1 = ["0 - Todos","1 - Todos alinhado" ,"2 - Fraco", "3 - Fraco alinhado" ,"4 - Forte" ,"5 - Forte alinhado"]
        combo1 = ttk.Combobox(frame_horarios, values=opcoes1, state="readonly", width=15)
        combo1.grid(row=6, column=1, sticky='w', padx=5, pady=2)

        # Define a seleção inicial baseada no IntVar
        combo1.current(intensao_var.get())  

        # Atualiza o IntVar automaticamente quando o usuário mudar (lambda é uma função anônima, sem nome)
        combo1.bind("<<ComboboxSelected>>", lambda e: intensao_var.set(combo1.current()))

        # Guarda a referência do IntVar (como antes)
        config_vars['INTENSAO'] = intensao_var


        #......................
        
        tk.Label(frame_horarios, text="SENSIBILIDADE:").grid(row=7, column=0, sticky='w', padx=5, pady=2)

        # Mantém o IntVar com o valor salvo (0,1,2)
        sensibilidade_var = tk.IntVar(value=SENSIBILIDADE_ENTRADA)  

        # Combobox com textos descritivos (sem textvariable)
        opcoes = ["Baixa" ,"Media", "Alta", "Mega" ,"Ultra" ]
        combo = ttk.Combobox(frame_horarios, values=opcoes, state="readonly", width=15)
        combo.grid(row=7, column=1, sticky='w', padx=5, pady=2)

        # Define a seleção inicial baseada no IntVar
        combo.current(sensibilidade_var.get())  

        # Atualiza o IntVar automaticamente quando o usuário mudar (lambda é uma função anônima, sem nome)
        combo.bind("<<ComboboxSelected>>", lambda e: sensibilidade_var.set(combo.current()))

        # Guarda a referência do IntVar (como antes)
        config_vars['SENSIBILIDADE_ENTRADA'] = sensibilidade_var


        #............................





        # ===== ABA 3: Configurações do Robô =====
        frame_robo = ttk.Frame(notebook)
        notebook.add(frame_robo, text="Configurações do Robô")
        
        tk.Label(frame_robo, text="Configurações Automáticas", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)
        
        # Booleanos
        tk.Label(frame_robo, text="AUTOMATIZAR:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        automatizar_var = tk.BooleanVar(value=AUTOMATIZAR)
        tk.Checkbutton(frame_robo, variable=automatizar_var).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        config_vars['AUTOMATIZAR'] = automatizar_var
        
        tk.Label(frame_robo, text="UMA_OPCAO_P_LETRA:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        uma_opcao_var = tk.BooleanVar(value=UMA_OPCAO_P_LETRA)
        tk.Checkbutton(frame_robo, variable=uma_opcao_var).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        config_vars['UMA_OPCAO_P_LETRA'] = uma_opcao_var
        
        tk.Label(frame_robo, text="FINALIZAR_OP_ROBO_STOP_LOSS:").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        finalizar_loss_var = tk.BooleanVar(value=FINALIZAR_OP_ROBO_STOP_LOSS)
        tk.Checkbutton(frame_robo, variable=finalizar_loss_var).grid(row=3, column=1, sticky='w', padx=5, pady=2)
        config_vars['FINALIZAR_OP_ROBO_STOP_LOSS'] = finalizar_loss_var
        
        tk.Label(frame_robo, text="FINALIZAR_OP_ROBO_STOP_MINI_SL:").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        finalizar_mini_var = tk.BooleanVar(value=FINALIZAR_OP_ROBO_STOP_MINI_SL)
        tk.Checkbutton(frame_robo, variable=finalizar_mini_var).grid(row=4, column=1, sticky='w', padx=5, pady=2)
        config_vars['FINALIZAR_OP_ROBO_STOP_MINI_SL'] = finalizar_mini_var
        
        tk.Label(frame_robo, text="FILTRAR_SINAIS:").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        filtrar_sinais_var = tk.BooleanVar(value=FILTRAR_SINAIS)
        tk.Checkbutton(frame_robo, variable=filtrar_sinais_var).grid(row=5, column=1, sticky='w', padx=5, pady=2)
        config_vars['FILTRAR_SINAIS'] = filtrar_sinais_var
        
        tk.Label(frame_robo, text="MANTER_OBS:").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        manter_obs_var = tk.BooleanVar(value=MANTER_OBS)
        tk.Checkbutton(frame_robo, variable=manter_obs_var).grid(row=6, column=1, sticky='w', padx=5, pady=2)
        config_vars['MANTER_OBS'] = manter_obs_var
        
        tk.Label(frame_robo, text="REFORCO_PROSITIVO:").grid(row=7, column=0, sticky='w', padx=5, pady=2)
        reforco_var = tk.BooleanVar(value=REFORCO_PROSITIVO)
        tk.Checkbutton(frame_robo, variable=reforco_var).grid(row=7, column=1, sticky='w', padx=5, pady=2)
        config_vars['REFORCO_PROSITIVO'] = reforco_var
        
        tk.Label(frame_robo, text="REGRA2CENTS:").grid(row=8, column=0, sticky='w', padx=5, pady=2)
        regra2cents_var = tk.BooleanVar(value=REGRA2CENTS)
        tk.Checkbutton(frame_robo, variable=regra2cents_var).grid(row=8, column=1, sticky='w', padx=5, pady=2)
        config_vars['REGRA2CENTS'] = regra2cents_var
        
        # Numéricos
        #tk.Label(frame_robo, text="QTD_AUTO:").grid(row=9, column=0, sticky='w', padx=5, pady=2)
        #qtd_auto_var = tk.IntVar(value=QTD_AUTO)
        #tk.Entry(frame_robo, textvariable=qtd_auto_var, width=10).grid(row=9, column=1, sticky='w', padx=5, pady=2)
        #config_vars['QTD_AUTO'] = qtd_auto_var
        
        tk.Label(frame_robo, text="QTD_AUTO:").grid(row=9, column=0, sticky='w', padx=2, pady=1)
        qtd_auto_var = tk.IntVar(value=QTD_AUTO)
        # Spinbox ocupa menos espaço que Entry
        tk.Spinbox(frame_robo, textvariable=qtd_auto_var, from_=100, to=10000, increment=100, width=10).grid(row=9, column=1, sticky='w', padx=2, pady=1)
        config_vars['QTD_AUTO'] = qtd_auto_var



        tk.Label(frame_robo, text="IDENTIFICADOR_ROBO:").grid(row=10, column=0, sticky='w', padx=5, pady=2)
        identificador_var = tk.DoubleVar(value=IDENTIFICADOR_ROBO)
        tk.Entry(frame_robo, textvariable=identificador_var, width=10).grid(row=10, column=1, sticky='w', padx=5, pady=2)
        config_vars['IDENTIFICADOR_ROBO'] = identificador_var
        
        tk.Label(frame_robo, text="QTD_ESPECIAL:").grid(row=11, column=0, sticky='w', padx=5, pady=2)
        qtd_especial_var = tk.IntVar(value=QTD_ESPECIAL)
        tk.Entry(frame_robo, textvariable=qtd_especial_var, width=10).grid(row=11, column=1, sticky='w', padx=5, pady=2)
        config_vars['QTD_ESPECIAL'] = qtd_especial_var
        
        tk.Label(frame_robo, text="PREJUIZO_MAX_ZERADO:").grid(row=12, column=0, sticky='w', padx=5, pady=2)
        prejuizo_var = tk.DoubleVar(value=PREJUIZO_MAX_ZERADO)
        tk.Entry(frame_robo, textvariable=prejuizo_var, width=10).grid(row=12, column=1, sticky='w', padx=5, pady=2)
        config_vars['PREJUIZO_MAX_ZERADO'] = prejuizo_var
        
        tk.Label(frame_robo, text="GATILHO_DIFF_PRECO:").grid(row=13, column=0, sticky='w', padx=5, pady=2)
        gatilho_var = tk.DoubleVar(value=GATILHO_DIFF_PRECO)
        tk.Entry(frame_robo, textvariable=gatilho_var, width=10).grid(row=13, column=1, sticky='w', padx=5, pady=2)
        config_vars['GATILHO_DIFF_PRECO'] = gatilho_var
        
        tk.Label(frame_robo, text="LIMIAR_PERDA:").grid(row=14, column=0, sticky='w', padx=5, pady=2)
        limiar_perda_var = tk.DoubleVar(value=LIMIAR_PERDA)
        tk.Entry(frame_robo, textvariable=limiar_perda_var, width=10).grid(row=14, column=1, sticky='w', padx=5, pady=2)
        config_vars['LIMIAR_PERDA'] = limiar_perda_var



        # ===== ABA 4: Parâmetros de Stop =====
        frame_stop = ttk.Frame(notebook)
        notebook.add(frame_stop, text="Parâmetros de Stop")
        
        tk.Label(frame_stop, text="Stop Loss e Mini Stop", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)
        
        tk.Label(frame_stop, text="STOP_LOSS_PADRAO (%):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        stop_loss_var = tk.DoubleVar(value=STOP_LOSS_PADRAO)
        tk.Entry(frame_stop, textvariable=stop_loss_var, width=10).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        config_vars['STOP_LOSS_PADRAO'] = stop_loss_var
        
        tk.Label(frame_stop, text="MINI_STOP_GAIN_PADRAO (%):").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        mini_stop_var = tk.DoubleVar(value=MINI_STOP_GAIN_PADRAO)
        tk.Entry(frame_stop, textvariable=mini_stop_var, width=10).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        config_vars['MINI_STOP_GAIN_PADRAO'] = mini_stop_var
        
        tk.Label(frame_stop, text="INTERVALO_BLOQUEIO (segundos):").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        intervalo_var = tk.IntVar(value=INTERVALO_BLOQUEIO)
        tk.Entry(frame_stop, textvariable=intervalo_var, width=10).grid(row=3, column=1, sticky='w', padx=5, pady=2)
        config_vars['INTERVALO_BLOQUEIO'] = intervalo_var
        
        tk.Label(frame_stop, text="LIMIAR_FORCA (%):").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        limiar_var = tk.DoubleVar(value=LIMIAR_FORCA)
        tk.Entry(frame_stop, textvariable=limiar_var, width=10).grid(row=4, column=1, sticky='w', padx=5, pady=2)
        config_vars['LIMIAR_FORCA'] = limiar_var
        
        # ===== BOTÕES DE AÇÃO =====
        #btn_frame = tk.Frame(config_window)
        #btn_frame.pack(fill='x', padx=5, pady=5)
        # Frame para os botões - fica fixo na parte inferior
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(side='bottom', fill='x', padx=5, pady=(0, 5))  # pady: 0 em cima, 5 embaixo


        def aplicar_configuracoes():
            """Aplica as configurações alteradas"""
            global TOKEN, BASE_URL, CHAT_ID_DEFAULT, TEXT_PATH, PATH, TEXT_ATIVAS
            global HORARIO_INICIO, HORARIO_FIM, MENOR_PRECO_ACEITO, MAIOR_PRECO_ACEITO, INTENSAO, SENSIBILIDADE_ENTRADA
            global AUTOMATIZAR, QTD_AUTO, IDENTIFICADOR_ROBO, REGRA2CENTS, QTD_ESPECIAL, PREJUIZO_MAX_ZERADO
            global UMA_OPCAO_P_LETRA, FINALIZAR_OP_ROBO_STOP_LOSS, FINALIZAR_OP_ROBO_STOP_MINI_SL, FILTRAR_SINAIS, MANTER_OBS, GATILHO_DIFF_PRECO, LIMIAR_PERDA
            global REFORCO_PROSITIVO, STOP_LOSS_PADRAO, MINI_STOP_GAIN_PADRAO, INTERVALO_BLOQUEIO, LIMIAR_FORCA
            
            try:
                # Atualizar variáveis globais
                TOKEN = config_vars['TOKEN'].get()
                BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"
                CHAT_ID_DEFAULT = config_vars['CHAT_ID_DEFAULT'].get()
                
                TEXT_PATH = config_vars['TEXT_PATH'].get()
                PATH = config_vars['PATH'].get()
                TEXT_ATIVAS = config_vars['TEXT_ATIVAS'].get()
                ATIVOS_PATH = config_vars['ATIVOS_PATH'].get()
                ATIVOS_FINALIZADOS_PATH = config_vars['ATIVOS_FINALIZADOS_PATH'].get()
                
                # Horários
                hh_ini = int(config_vars['HORARIO_INICIO_HH'].get())
                mm_ini = int(config_vars['HORARIO_INICIO_MM'].get())
                HORARIO_INICIO = datetime.time(hh_ini, mm_ini)
                
                hh_fim = int(config_vars['HORARIO_FIM_HH'].get())
                mm_fim = int(config_vars['HORARIO_FIM_MM'].get())
                HORARIO_FIM = datetime.time(hh_fim, mm_fim)
                
                # Preços
                MENOR_PRECO_ACEITO = config_vars['MENOR_PRECO_ACEITO'].get()
                MAIOR_PRECO_ACEITO = config_vars['MAIOR_PRECO_ACEITO'].get()
                
                #INTENSAO
                INTENSAO = config_vars['INTENSAO'].get()

                SENSIBILIDADE_ENTRADA= config_vars['SENSIBILIDADE_ENTRADA'].get()

                # Booleanos
                AUTOMATIZAR = config_vars['AUTOMATIZAR'].get()
                UMA_OPCAO_P_LETRA = config_vars['UMA_OPCAO_P_LETRA'].get()
                FINALIZAR_OP_ROBO_STOP_LOSS = config_vars['FINALIZAR_OP_ROBO_STOP_LOSS'].get()
                FINALIZAR_OP_ROBO_STOP_MINI_SL = config_vars['FINALIZAR_OP_ROBO_STOP_MINI_SL'].get()
                FILTRAR_SINAIS = config_vars['FILTRAR_SINAIS'].get()
                MANTER_OBS = config_vars['MANTER_OBS'].get()
                REFORCO_PROSITIVO = config_vars['REFORCO_PROSITIVO'].get()
                REGRA2CENTS = config_vars['REGRA2CENTS'].get()
                
                # Numéricos
                QTD_AUTO = config_vars['QTD_AUTO'].get()
                IDENTIFICADOR_ROBO = config_vars['IDENTIFICADOR_ROBO'].get()
                QTD_ESPECIAL = config_vars['QTD_ESPECIAL'].get()
                PREJUIZO_MAX_ZERADO = config_vars['PREJUIZO_MAX_ZERADO'].get()
                GATILHO_DIFF_PRECO = config_vars['GATILHO_DIFF_PRECO'].get()
                LIMIAR_PERDA = config_vars['LIMIAR_PERDA'].get()
                
                # Parâmetros de stop
                STOP_LOSS_PADRAO = config_vars['STOP_LOSS_PADRAO'].get()
                MINI_STOP_GAIN_PADRAO = config_vars['MINI_STOP_GAIN_PADRAO'].get()
                INTERVALO_BLOQUEIO = config_vars['INTERVALO_BLOQUEIO'].get()
                LIMIAR_FORCA = config_vars['LIMIAR_FORCA'].get()
                
                # Atualizar PREJUIZO_MAX_ZERADO se baseado em QTD_AUTO
                PREJUIZO_MAX_ZERADO = QTD_AUTO * 0.04  # Mantém o cálculo original
                
                tk.messagebox.showinfo("Sucesso", "Configurações aplicadas com sucesso!")
                config_window.destroy()
                
                # Atualizar a tabela para refletir mudanças
                atualizar_tabela()
                salvar_para_arquivo()
                
            except Exception as e:
                tk.messagebox.showerror("Erro", f"Erro ao aplicar configurações: {str(e)}")
        
        def salvar_para_arquivo():
            """Salva configurações em um arquivo JSON"""
            try:
                config_data = {
                    'TOKEN': config_vars['TOKEN'].get(),
                    'CHAT_ID_DEFAULT': config_vars['CHAT_ID_DEFAULT'].get(),
                    'TEXT_PATH': config_vars['TEXT_PATH'].get(),
                    'PATH': config_vars['PATH'].get(),
                    'TEXT_ATIVAS': config_vars['TEXT_ATIVAS'].get(),
                    'ATIVOS_PATH': config_vars['ATIVOS_PATH'].get(),
                    'ATIVOS_FINALIZADOS_PATH': config_vars['ATIVOS_FINALIZADOS_PATH'].get(),
                    'HORARIO_INICIO': f"{config_vars['HORARIO_INICIO_HH'].get()}:{config_vars['HORARIO_INICIO_MM'].get()}",
                    'HORARIO_FIM': f"{config_vars['HORARIO_FIM_HH'].get()}:{config_vars['HORARIO_FIM_MM'].get()}",
                    'MENOR_PRECO_ACEITO': config_vars['MENOR_PRECO_ACEITO'].get(),
                    'MAIOR_PRECO_ACEITO': config_vars['MAIOR_PRECO_ACEITO'].get(),
                    'INTENSAO':config_vars['INTENSAO'].get(),
                    'SENSIBILIDADE_ENTRADA': config_vars['SENSIBILIDADE_ENTRADA'].get(),


                    'AUTOMATIZAR': config_vars['AUTOMATIZAR'].get(),
                    'QTD_AUTO': config_vars['QTD_AUTO'].get(),
                    'IDENTIFICADOR_ROBO': config_vars['IDENTIFICADOR_ROBO'].get(),
                    'REGRA2CENTS': config_vars['REGRA2CENTS'].get(),
                    'QTD_ESPECIAL': config_vars['QTD_ESPECIAL'].get(),
                    'PREJUIZO_MAX_ZERADO': config_vars['PREJUIZO_MAX_ZERADO'].get(),
                    'UMA_OPCAO_P_LETRA': config_vars['UMA_OPCAO_P_LETRA'].get(),
                    'FINALIZAR_OP_ROBO_STOP_LOSS': config_vars['FINALIZAR_OP_ROBO_STOP_LOSS'].get(),
                    'FINALIZAR_OP_ROBO_STOP_MINI_SL': config_vars['FINALIZAR_OP_ROBO_STOP_MINI_SL'].get(),
                    'FILTRAR_SINAIS': config_vars['FILTRAR_SINAIS'].get(),
                    'MANTER_OBS': config_vars['MANTER_OBS'].get(),
                    'GATILHO_DIFF_PRECO': config_vars['GATILHO_DIFF_PRECO'].get(),
                    'LIMIAR_PERDA': config_vars['LIMIAR_PERDA'].get(),
                    'REFORCO_PROSITIVO': config_vars['REFORCO_PROSITIVO'].get(),
                    'STOP_LOSS_PADRAO': config_vars['STOP_LOSS_PADRAO'].get(),
                    'MINI_STOP_GAIN_PADRAO': config_vars['MINI_STOP_GAIN_PADRAO'].get(),
                    'INTERVALO_BLOQUEIO': config_vars['INTERVALO_BLOQUEIO'].get(),
                    'LIMIAR_FORCA': config_vars['LIMIAR_FORCA'].get()
                }
                
                import json
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                
                tk.messagebox.showinfo("Sucesso", "Configurações salvas em config.json!")
                
            except Exception as e:
                tk.messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")
        
        def carregar_de_arquivo():
            """Carrega configurações de um arquivo JSON"""
            try:
                import json
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # Atualizar campos
                    for key, value in config_data.items():
                        if key in config_vars:
                            if key == 'HORARIO_INICIO':
                                hh, mm = value.split(':')
                                config_vars['HORARIO_INICIO_HH'].set(hh)
                                config_vars['HORARIO_INICIO_MM'].set(mm)
                            elif key == 'HORARIO_FIM':
                                hh, mm = value.split(':')
                                config_vars['HORARIO_FIM_HH'].set(hh)
                                config_vars['HORARIO_FIM_MM'].set(mm)
                            else:
                                config_vars[key].set(value)
                    
                    tk.messagebox.showinfo("Sucesso", "Configurações carregadas!")
                else:
                    tk.messagebox.showwarning("Aviso", "Arquivo config.json não encontrado.")
                    
            except Exception as e:
                tk.messagebox.showerror("Erro", f"Erro ao carregar: {str(e)}")
        
        # Botões
        #tk.Button(btn_frame, text="Carregar de Arquivo", command=carregar_de_arquivo).pack(side='left', padx=5)
        #tk.Button(btn_frame, text="Salvar para Arquivo", command=salvar_para_arquivo).pack(side='left', padx=5)
        #tk.Button(btn_frame, text="Aplicar", command=aplicar_configuracoes, bg='green', fg='white').pack(side='left', padx=5)
        #tk.Button(btn_frame, text="Cancelar", command=config_window.destroy, bg='red', fg='white').pack(side='left', padx=5)


        tk.Button(btn_frame, text="Carregar", command=carregar_de_arquivo).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Salvar", command=salvar_para_arquivo).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Aplicar", command=aplicar_configuracoes, bg='green', fg='white').pack(side='left', padx=5)
        tk.Button(btn_frame, text="Cancelar", command=config_window.destroy, bg='red', fg='white').pack(side='left', padx=5)
    # --- Frame para tabela + scrollbar ---
    frame_tabela = tk.Frame(root)
    frame_tabela.pack(expand=True, fill="both", padx=8, pady=8)

    # Vars internas da GUI (IntVar) e espelho para booleans globais
    var_apenas_msgs_stop = tk.IntVar(value=1 if APENAS_MSGS_STOP else 0)
    var_msgs = tk.IntVar(value=1 if MOSTRAR_MSGS else 0)
    var_fotos = tk.IntVar(value=1 if MOSTRAR_FOTOS else 0)
    var_fotos_carteira = tk.IntVar(value=1 if MOSTRAR_FOTOS_CARTEIRA else 0)
    var_python = tk.IntVar(value=1 if MOSTRAR_PYTHON else 0)
    var_filtrar = tk.IntVar(value=1 if FILTRAR_MENSAGEM else 0)
    var_som = tk.IntVar(value=1 if SOM else 0)
    var_mensagem = tk.StringVar(value=NOVA_MSG)
    

    def sync_flags():
        globals()["MOSTRAR_MSGS"] = bool(var_msgs.get())
        globals()["APENAS_MSGS_STOP"] = bool(var_apenas_msgs_stop.get())
        globals()["MOSTRAR_FOTOS"] = bool(var_fotos.get())
        globals()["MOSTRAR_FOTOS_CARTEIRA"] = bool(var_fotos_carteira.get())
        globals()["MOSTRAR_PYTHON"] = bool(var_python.get())
        globals()["FILTRAR_MENSAGEM"] = bool(var_filtrar.get())
        globals()["SOM"] = bool(var_som.get())
        globals()["NOVA_MSG"]= str(var_mensagem.get()) 
    # Frame de opções
    options_frame = tk.Frame(root)
    options_frame.pack(fill="x", padx=8, pady=8)

    tk.Checkbutton(options_frame, text="📩 Somente stops",
                   variable=var_apenas_msgs_stop, command=sync_flags).pack(side="left", padx=5)
    tk.Checkbutton(options_frame, text="📩 Mensagens recebidas",
                   variable=var_msgs, command=sync_flags).pack(side="left", padx=5)
    tk.Checkbutton(options_frame, text="🖼️ Fotos recebidas",
                   variable=var_fotos, command=sync_flags).pack(side="left", padx=5)
    tk.Checkbutton(options_frame, text="🖼️ Apenas Fotos carteira",
                   variable=var_fotos_carteira, command=sync_flags).pack(side="left", padx=5)
    
    tk.Checkbutton(options_frame, text="⚙️ Mensagens Python",
                   variable=var_python, command=sync_flags).pack(side="left", padx=5)
    tk.Checkbutton(options_frame, text="⚙️ Filtrar mensagens",
                   variable=var_filtrar, command=sync_flags).pack(side="left", padx=5)
    tk.Checkbutton(options_frame, text="⚙️ SOM",
                   variable=var_som, command=sync_flags).pack(side="left", padx=5)
    config_button = tk.Button(options_frame, text="⚙️ Configurações", command=abrir_janela_config, bg='blue', fg='white')
    config_button.pack(side='left', padx=10)

    sync_flags()
    # Label de alerta especial
    alerta_label = tk.Label(root, text="", font=("Arial", 16, "bold"),
                            fg="white", bg="black")
    alerta_label.pack(fill="x", pady=5)
    
    
# Inserir o valor da variável interna no campo
    
# Criar o campo Entry vinculado à StringVar
    entrada = tk.Entry(root, textvariable=var_mensagem, width=300)
    entrada.pack(pady=10)



# achar de onde vem ganho atual e fazer a varredura com votar_easfasd e verificar se a saida mudou de compra para venda se o ativo esta comprado   
    
    # --- Tabela principal ---
    cols = ("Ativo", "Entrada", "Atual", "Qtd", "Tipo", "Status", "Ganho Atual", "Máx Ganho", "Stop", "Mini Stop %", "VCV")

    tree = ttk.Treeview(frame_tabela, columns=cols, show="headings", height=6)
    for col in cols:
        tree.heading(col, text=col)

    tree.column("Ativo", width=50, anchor="center")
    tree.column("Entrada", width=50, anchor="e")
    tree.column("Atual", width=50, anchor="e")
    tree.column("Qtd", width=40, anchor="center")
    tree.column("Tipo", width=40, anchor="center")
    tree.column("Status", width=50, anchor="center")
    tree.column("Ganho Atual", width=90, anchor="e")
    tree.column("Máx Ganho", width=90, anchor="e")
    tree.column("Stop", width=150, anchor="e")
    tree.column("Mini Stop %", width=90, anchor="center")
    tree.column("VCV", width=90, anchor="center")

    tree.pack(expand=True, fill="both", padx=8, pady=8)
    """tree.tag_configure("negativo", foreground="red")
    tree.tag_configure("positivo", foreground="green")
    tree.tag_configure("mini_stop", foreground="orange")"""

    tree.tag_configure("negativo", background="lightcoral")   # fundo vermelho claro
    tree.tag_configure("positivo", background="lightgreen")   # fundo verde claro
    tree.tag_configure("mini_stop", background="orange")      # fundo laranja
    
    # --- Scrollbar vertical ---
    scrollbar_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)

    # posiciona lado a lado
    tree.pack(side="left", expand=True, fill="both")
    scrollbar_y.pack(side="right", fill="y")

    atualizar_job = None  # id da atualização da tabela principal

    # --- Edição de células (Entrada e Qtd) com pausa/retomada ---
    def editar_celula(event):
        nonlocal atualizar_job
        item_id = tree.identify_row(event.y)
        col = tree.identify_column(event.x)

        if not item_id or col not in ("#2", "#4","#8" ,"#10"):  # Entrada, Qtd, Max ganho,Mini Stop %
            return

        # pausa atualização automática da tabela principal
        if atualizar_job:
            root.after_cancel(atualizar_job)

        x, y, width, height = tree.bbox(item_id, col)
        valor_atual = tree.set(item_id, col)

        entry = tk.Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, valor_atual)
        entry.focus()

        def salvar_edicao(event=None):
            nonlocal atualizar_job
            novo_valor = entry.get().strip()
            if novo_valor and item_id in tree.get_children():
                tree.set(item_id, col, novo_valor)
                ativo = tree.set(item_id, "Ativo")
                try:
                    if col == "#2":  # Entrada
                        ATIVOS[ativo]["entrada"] = float(novo_valor)
                    elif col == "#4":  # Qtd
                        ATIVOS[ativo]["qtd"] = float(novo_valor)
                    elif col == "#8":  # Qtd
                        ATIVOS[ativo]["max_diff"] = float(novo_valor)
                    
                    elif col == "#10":  # Mini Stop %
                        ATIVOS[ativo]["mini_stop_pct"] = float(novo_valor)    
                    salvar_ativos()
                except Exception as e:
                    print("⚠️ Erro ao salvar edição:", e)
            entry.destroy()
            # retoma atualização automática
            atualizar_job = root.after(10000, atualizar_tabela)

        entry.bind("<Return>", salvar_edicao)
        entry.bind("<FocusOut>", salvar_edicao)

    tree.bind("<Double-1>", editar_celula)

    """# --- Rodapé principal ---
    bottom = tk.Frame(root)
    bottom.pack(fill="x", padx=8, pady=8)

    total_label = tk.Label(bottom, text="💰 Ganho Total: 0.00", font=("Arial", 13, "bold"))
    total_label.pack(side="left")
    btn = ttk.Button(bottom, text="🔄 Atualizar Agora", command=lambda: atualizar_tabela())
    btn.pack(side="right")"""

    # --- Rodapé principal ---
    bottom = tk.Frame(root)
    bottom.pack(fill="x", padx=8, pady=8)

    total_label = tk.Label(bottom, text="💰 Ganho Total: 0.00", font=("Arial", 13, "bold"))
    total_label.pack(side="left")

    total_positivo_label = tk.Label(bottom, text="    Positivo: 0.00", font=("Arial", 13, "bold"))
    total_positivo_label.pack(side="left")

    total_negativo_label = tk.Label(bottom, text="    Negativo: 0.00", font=("Arial", 13, "bold"))
    total_negativo_label.pack(side="left")
    
    total_fim_label = tk.Label(bottom, text="    Finalizados: 0.00", font=("Arial", 13, "bold"))
    total_fim_label.pack(side="left")
    
    #melhor_entrada_label = tk.Label(bottom, text="    Melhor entrada: ", font=("Arial", 10, "bold"))
    #melhor_entrada_label.pack(side="left")
    
    btn = ttk.Button(bottom, text="🔄 Atualizar Agora", command=lambda: atualizar_tabela())
    btn.pack(side="right")

    bottom_row = tk.Frame(bottom)
    bottom_row.pack(fill="x", pady=(5, 0))  # 5px de espaço acima

    melhor_entrada_label = tk.Label(bottom_row, text="    Melhor entrada: ", font=("Arial", 8, "bold"))
    melhor_entrada_label.pack(side="top", anchor="center")


    # --- Frame para Observados + Finalizados lado a lado ---
    #obs_fin_frame = tk.Frame(root)
    #obs_fin_frame.pack(expand=True, fill="x", padx=8, pady=8)
    
    #----------
        # --- Frame para Observados + Finalizados lado a lado ---
    obs_fin_frame = tk.Frame(root)
    obs_fin_frame.pack(expand=True, fill="x", padx=8, pady=8)

    # --- Frame para controles da tabela de observados (com botão +) ---
    obs_controls_frame = tk.Frame(obs_fin_frame)
    obs_controls_frame.pack(side="top", fill="x", padx=5, pady=(0, 5))
    
    # Label e Entry para adicionar novo ativo
    tk.Label(obs_controls_frame, text="Adicionar:").pack(side="left", padx=(0, 5))
    
    novo_ativo_var = tk.StringVar()
    novo_ativo_entry = tk.Entry(obs_controls_frame, textvariable=novo_ativo_var, width=15)
    novo_ativo_entry.pack(side="left", padx=(0, 5))

    # Cache para análises (evita chamar múltiplas vezes o mesmo ativo)

    def analisar_ativo_rapido():
        
        ativo = novo_ativo_var.get().strip().upper()
        
        if not ativo:
            messagebox.showwarning("Aviso", "Digite um código de ativo")
            return
        
        preco = preco_medio(ativo)
        if preco is None:
            messagebox.showerror("Erro", f"Ativo {ativo} não encontrado")
            return
        
        # Usar a função votar_compra_ou_vender que você já tem
        voto = votar_compra_ou_vender(ativo)
        v2=obter_melhor_operacao(ativo)
        # Analisar AMBAS as operações
        analise_compra = analise_hibrida_completa(ativo, "compra")
        analise_venda = analise_hibrida_completa(ativo, "venda")
        
        mensagem = f"📊 ANÁLISE COMPLETA - {ativo}\n"
        mensagem += f"Preço atual: {preco:.2f}\n"
        mensagem += f"Voto do sistema: {voto}  {v2}\n\n"
        
        # Análise para COMPRA
        mensagem += "═" * 40 + "\n"
        mensagem += "📈 ANÁLISE PARA COMPRA:\n"
        if analise_compra and 'decisao_final' in analise_compra:
            mensagem += f"  Decisão: {analise_compra['decisao_final']}\n"
            if 'analise_book' in analise_compra:
                book_info = analise_compra['analise_book'].get('classificacao_book', {})
                mensagem += f"  Classificação Book: {book_info.get('classificacao', 'N/A')}\n"
                mensagem += f"  Pontuação: {book_info.get('pontuacao_total', 0):.1f}/10\n"
        else:
            mensagem += "  Análise de compra não disponível\n"
        
        # Análise para VENDA
        mensagem += "\n" + "═" * 40 + "\n"
        mensagem += "📉 ANÁLISE PARA VENDA:\n"
        if analise_venda and 'decisao_final' in analise_venda:
            mensagem += f"  Decisão: {analise_venda['decisao_final']}\n"
            if 'analise_book' in analise_venda:
                book_info = analise_venda['analise_book'].get('classificacao_book', {})
                mensagem += f"  Classificação Book: {book_info.get('classificacao', 'N/A')}\n"
                mensagem += f"  Pontuação: {book_info.get('pontuacao_total', 0):.1f}/10\n"
        else:
            mensagem += "  Análise de venda não disponível\n"
        
        # Recomendação baseada na comparação
        mensagem += "\n" + "═" * 40 + "\n"
        mensagem += "🎯 RECOMENDAÇÃO FINAL:\n"
        
        if analise_compra and analise_venda:
            compra_forte = analise_compra.get('decisao_final') in ["EXECUTAR_ORDEM", "EXECUTAR_COM_CUIDADO"]
            venda_forte = analise_venda.get('decisao_final') in ["EXECUTAR_ORDEM", "EXECUTAR_COM_CUIDADO"]
            
            if compra_forte and not venda_forte:
                mensagem += "  ✅ PREFERIR COMPRA (análise de compra mais forte)\n"
            elif venda_forte and not compra_forte:
                mensagem += "  ✅ PREFERIR VENDA (análise de venda mais forte)\n"
            elif compra_forte and venda_forte:
                mensagem += "  ⚠️ AMBAS ANÁLISES FORTES - AGUARDAR CONFIRMAÇÃO\n"
            else:
                mensagem += "  ⛔ EVITAR OPERAÇÃO (ambas análises fracas)\n"
        else:
            mensagem += "  ℹ️ Análise incompleta\n"
        
        messagebox.showinfo(f"Análise Completa - {ativo}", mensagem)    

    
    btn_analisar = tk.Button(obs_controls_frame, text="🔍", command=analisar_ativo_rapido,
                           bg="blue", fg="white", width=3)
    btn_analisar.pack(side="left", padx=5)    
    

    def adicionar_ativo_manual():
        """Adiciona um ativo manualmente à tabela de observados"""
        ativo = novo_ativo_var.get().strip().upper()
        
        if not ativo:
            messagebox.showwarning("Aviso", "Digite um código de ativo")
            return
        
        # Verificar se já existe
        if ativo in OBSERVAR or ativo in ATIVOS:
            messagebox.showwarning("Aviso", f"Ativo {ativo} já está sendo monitorado")
            return
        
        # Verificar se o ativo existe no MT5
        preco = preco_medio(ativo)
        if preco is None or preco == 0:
            messagebox.showerror("Erro", f"Ativo {ativo} não encontrado ou preço indisponível")
            return
        
        # Verificar faixa de preço
        prc = preco_real(ativo, "compra")
        prv = preco_real(ativo, "venda")
        prx = prc * prv
        
        if not (MENOR_PRECO_ACEITO <= preco <= MAIOR_PRECO_ACEITO) or prx == 0.0:
            messagebox.showwarning("Aviso", f"Ativo {ativo} fora da faixa de preço aceita ({MENOR_PRECO_ACEITO:.2f} a {MAIOR_PRECO_ACEITO:.2f})")
            return
        
        # Adicionar ao OBSERVAR
        OBSERVAR[ativo] = {
            "preco_inicial": preco,
            "status": "indefinido",
            "ultimo_diff": 0.0,
            "reset": 0,
            "intensidade": 0.0,
            "int_geral": 0.0
        }
        
        # Limpar campo de entrada
        novo_ativo_var.set("")
        
        # Atualizar tabela de observados
        atualizar_tabela_obs()
        
        # Dar foco de volta ao campo
        novo_ativo_entry.focus()
        
        # Mostrar mensagem de sucesso
        messagebox.showinfo("Sucesso", f"Ativo {ativo} adicionado para observação")
    
    # Botão para adicionar
    btn_adicionar = tk.Button(obs_controls_frame, text="+", command=adicionar_ativo_manual, 
                            bg="green", fg="white", width=3, font=("Arial", 10, "bold"))
    btn_adicionar.pack(side="left", padx=(0, 5))
    
    # Botão para remover ativo selecionado
    def remover_ativo_observado():
        """Remove o ativo selecionado da tabela de observados"""
        selecionado = tree_obs.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um ativo para remover")
            return
        
        item = selecionado[0]
        ativo = tree_obs.item(item, "values")[0]
        
        if ativo in OBSERVAR:
            del OBSERVAR[ativo]
            atualizar_tabela_obs()
            messagebox.showinfo("Sucesso", f"Ativo {ativo} removido da observação")
    
    btn_remover = tk.Button(obs_controls_frame, text="🗑️", command=remover_ativo_observado,
                          bg="red", fg="white", width=3)
    btn_remover.pack(side="left")
    
    # Adicionar atalho de tecla Enter no campo de entrada
    def adicionar_com_enter(event):
        adicionar_ativo_manual()
    
    novo_ativo_entry.bind("<Return>", adicionar_com_enter)

    # --- Tabela de Observados ---
    cols_obs = ("Ativo", "Inicial", "Atual", "N_rs", "Status", "Intens", "Int_princ")
    tree_obs = ttk.Treeview(obs_fin_frame, columns=cols_obs, show="headings", height=6)
    
    for col in cols_obs:
        tree_obs.heading(col, text=col)

    tree_obs.column("Ativo", width=40, anchor="center")
    tree_obs.column("Inicial", width=40, anchor="e")
    tree_obs.column("Atual", width=40, anchor="e")
    tree_obs.column("N_rs", width=30, anchor="center")
    tree_obs.column("Status", width=40, anchor="center")
    tree_obs.column("Intens", width=40, anchor="center")
    tree_obs.column("Int_princ", width=40, anchor="center")
    
    tree_obs.pack(side="left", expand=True, fill="both", padx=5)

    #----------
     # --- Tabela de Observados ---
    #cols_obs = ("Ativo", "Inicial", "Atual","N_rs", "Status","Intens","Int_princ"  )
    #tree_obs = ttk.Treeview(obs_fin_frame, columns=cols_obs, show="headings", height=6)
    #for col in cols_obs:
    #    tree_obs.heading(col, text=col)

    #tree_obs.column("Ativo", width=40, anchor="center")
    #tree_obs.column("Inicial", width=40, anchor="e")
    #tree_obs.column("Atual", width=40, anchor="e")
    #tree_obs.column("N_rs", width=30, anchor="center")
    #tree_obs.column("Status", width=40, anchor="center")
    #tree_obs.column("Intens", width=40, anchor="center")
    #tree_obs.column("Int_princ", width=40, anchor="center")
    #tree_obs.pack(side="left", expand=True, fill="both", padx=5)

    atualizar_obs_job = None
      # id da atualização da tabela observados

    # (Opcional) permitir editar preço inicial na tabela observados com pausa/retomada
        
    def editar_celula_obs(event):
        nonlocal atualizar_obs_job
        item_id = tree_obs.identify_row(event.y)
        col = tree_obs.identify_column(event.x)

        if not item_id or col not in ("#2",):  # só coluna Inicial (#2)
            return

        if atualizar_obs_job:
            root.after_cancel(atualizar_obs_job)

        x, y, width, height = tree_obs.bbox(item_id, col)
        valor_atual = tree_obs.set(item_id, col)

        entry = tk.Entry(tree_obs)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, valor_atual)
        entry.focus()

        def salvar_edicao_obs(event=None):
            nonlocal atualizar_obs_job
            novo_valor = entry.get().strip()
            if novo_valor and item_id in tree_obs.get_children():
                tree_obs.set(item_id, col, novo_valor)
                ativo = tree_obs.set(item_id, "Ativo")
                try:
                    if ativo in OBSERVAR:
                        OBSERVAR[ativo]["preco_inicial"] = float(novo_valor)
                except Exception as e:
                    print("⚠️ Erro ao salvar edição observados:", e)
            entry.destroy()
            atualizar_obs_job = root.after(10000, atualizar_tabela_obs)

        entry.bind("<Return>", salvar_edicao_obs)
        entry.bind("<FocusOut>", salvar_edicao_obs)

    tree_obs.bind("<Double-1>", editar_celula_obs)
    
    # --- Tabela Finalizados com Scrollbar ---
    cols_fin = ("Ativo", "Entrada", "Qtd", "Tipo", "Resultado", "Mini Stop %", "Status Final","Intens" ,"Hist vcv sta1 cas")

    # Frame para tabela + scrollbar
    fin_frame = tk.Frame(obs_fin_frame)
    fin_frame.pack(side="left", expand=True, fill="both", padx=5)

# Scrollbar vertical
    scrollbar_fin = ttk.Scrollbar(fin_frame, orient="vertical")
    scrollbar_fin.pack(side="right", fill="y")

# Treeview
    tree_finalizados = ttk.Treeview(
    fin_frame,
    columns=cols_fin,
    show="headings",
    height=6,
    yscrollcommand=scrollbar_fin.set  # conecta a barra
)
    
    # --- Tabela de Finalizados ---
    #cols_fin = ("Ativo", "Entrada", "Qtd", "Tipo", "Resultado", "Mini Stop %", "Status Final")
    #tree_finalizados = ttk.Treeview(obs_fin_frame, columns=cols_fin, show="headings", height=8)
    #tree_finalizados = ttk.Treeview(obs_fin_frame, columns=cols_fin, show="headings", height=6)




    
    
    for col in cols_fin:
        tree_finalizados.heading(col, text=col)

    tree_finalizados.column("Ativo", width=50, anchor="center")
    tree_finalizados.column("Entrada", width=40, anchor="e")
    tree_finalizados.column("Qtd", width=40, anchor="center")
    tree_finalizados.column("Tipo", width=25, anchor="center")
    tree_finalizados.column("Resultado", width=40, anchor="e")
    tree_finalizados.column("Mini Stop %", width=60, anchor="center")
    tree_finalizados.column("Status Final", width=50, anchor="center")
    tree_finalizados.column("Intens", width=40, anchor="center")
    tree_finalizados.column("Hist vcv sta1 cas", width=100, anchor="center")
    # cores
    tree_finalizados.tag_configure("positivo", background="lightgreen")
    tree_finalizados.tag_configure("negativo", background="lightcoral")

    tree_finalizados.pack(side="left", expand=True, fill="both", padx=5)

    # Conectar scrollbar ao treeview
    scrollbar_fin.config(command=tree_finalizados.yview)

    # --- Função para atualizar tabela de finalizados ---
    
    def atualizar_tabela_finalizados():
        for item in tree_finalizados.get_children():
            tree_finalizados.delete(item)
        for op_id, dados in FINALIZADOS.items():
            status_tag = "positivo" if dados.get("ultimo_status") == "positivo" else "negativo"
            robo = "🤖" if dados.get("mini_stop_pct", 0.0)==IDENTIFICADOR_ROBO else ""
            tree_finalizados.insert("", "end", values=(
                dados.get("ativo", ""),
                f"{dados.get('entrada', 0.0):.2f}{robo}",
                dados.get("qtd", 0.0),
                dados.get("tipo", ""),
                f"{dados.get('r_fim', 0.0):.2f}",   # resultado com 2 casas decimais
                dados.get("mini_stop_pct", 0.0) ,
                dados.get("ultimo_status", ""),
                dados.get("intensidade", 0.0),
                dados.get("historico", "")
                
            ), tags=(status_tag,))

        


    

    # --- Função para limpar finalizados ---
    def limpar_finalizados():
        global FINALIZADOS
        FINALIZADOS.clear()
        with open("finalizados.json", "w", encoding="utf-8") as f:
            #json.dump({}, f, ensure_ascii=False, indent=4)

            json.dump({}, f, ensure_ascii=False, indent=4, default=str)

            
        atualizar_tabela_finalizados()

    # --- Botão para limpar finalizados ---
    bottom = tk.Frame(root)
    bottom.pack(fill="x", padx=8, pady=8)

    btn_limpar = ttk.Button(bottom, text="🗑️ Limpar Finalizados", command=limpar_finalizados)
    btn_limpar.pack(side="right", padx=5)
    # preencher tabela logo na inicialização
    carregar_finalizados()
    atualizar_tabela_finalizados()



    
    # Chamar essa função sempre que finalizar_ativo for usado
    # Basta adicionar dentro de finalizar_ativo:
    # atualizar_tabela_finalizados()

    # --- Área imagem ---
    img_frame = tk.Frame(root, height=400, bg="lightgray")
    img_frame.pack(fill="x", padx=8, pady=8)

    img_label = tk.Label(img_frame, text="Última imagem recebida aparecerá aqui", bg="lightgray")
    img_label.pack()

    legenda_label = tk.Label(img_frame, text="Nenhuma imagem recebida ainda", bg="lightgray", font=("Arial", 10))
    legenda_label.pack()


    

    # --- Funções de atualização ---
    def atualizar_tabela():
        nonlocal atualizar_job
        var_mensagem.set(NOVA_MSG)
        for i in tree.get_children():
            tree.delete(i)
        total_ganho = 0.0
        for ativo, dados in list(ATIVOS.items()):

            preco = preco_medio(ativo)
            
            if preco:
                entrada = dados["entrada"]
                tipo    = dados["tipo"]
                qtd     = dados.get("qtd", 1.0)
                diff_unit = preco - entrada if tipo == "compra" else entrada - preco
                diff = diff_unit * qtd
                max_diff = dados.get("max_diff", 0.0)
                status   = "positivo" if diff > 0 else "negativo"
                total_ganho += diff

                stop_loss_valor = dados["stop_loss_valor"]
                stop_loss_pct   = dados["stop_loss_pct"]
                mini_stop_pct   = dados.get("mini_stop_pct", 30.0)
                mini_stop_valor = max_diff * (1 - mini_stop_pct/100.0) if max_diff > 0 else 0.0
                 
                #valor_saida = ( (entrada * qtd) +   mini_stop_valor)/qtd
                #valor_saida = entrada + (mini_stop_valor/qtd) if tipo == 'compra' else entrada - (mini_stop_valor/qtd)
                

                valor_saida = (entrada + (mini_stop_valor/qtd) if tipo == 'compra' else entrada - (mini_stop_valor/qtd)) if max_diff > 0 else entrada
                #if tipo == 'compra':
                # Para compra: saída (venda) deve ser acima da entrada
                # Queremos vender a um preço que dê o lucro mínimo aceitável
                #    valor_saida = entrada + (mini_stop_valor / qtd) if max_diff > 0 else entrada
                #else:  # venda
                # Para venda: saída (compra) deve ser abaixo da entrada
                # Queremos comprar a um preço que dê o lucro mínimo aceitável
                #    valor_saida = entrada - (mini_stop_valor / qtd) if max_diff > 0 else entrada

                max_mini_stop_valor= dados["max_diff"] * (1 - 35/100.0)

                robo = "🤖" if mini_stop_pct==IDENTIFICADOR_ROBO else ""
                stop_info = f"{stop_loss_valor:.2f} ({stop_loss_pct:.0f}%) | {mini_stop_valor:.2f} ({mini_stop_pct:.0f}%)|(max) { max_mini_stop_valor:.2f}    "
                vcvi= rompimento_saida(ativo, 1, timeframe=2)  #2 #obter_melhor_operacao(ativo) #votar_compra_ou_vender(ativo)
                item_id = tree.insert("", "end", values=(
                    ativo, f"{entrada:.2f}", f"R$ {preco:.2f}", f"{qtd}", tipo, status,
                    f"{diff:.2f}", f"{max_diff:.2f}", stop_info, f"{mini_stop_pct:.0f}% |R$ {valor_saida:.2f} {robo}", vcvi
                ))

                if status == "negativo":
                    tree.item(item_id, tags=("negativo",))
                elif diff < mini_stop_valor and max_diff > 0:
                    tree.item(item_id, tags=("mini_stop",))
                else:
                    tree.item(item_id, tags=("positivo",))

        total_label.config(text=f"💰 Ganho Total: {total_ganho:.2f}")
        
        
        r_fim_valores = [item['r_fim'] for item in FINALIZADOS.values()]
        total_fim_label.config(text=f" Total finalizado: {sum(r_fim_valores):.2f}")
    

        total_positivo_label.config(text=f"    Positivo: {sum(v for v in r_fim_valores if v > 0):.2f}")
        total_negativo_label.config(text=f"    Negativo: {sum(v for v in r_fim_valores if v < 0):.2f}" )

        stats = rede.get_estatisticas()
        
        melhor_entrada_label.config(text=  f"🧠 **ESTATÍSTICAS DA IA**\n"
                f"{'='*30}\n"
                f"📊 Total de operações: {stats.get('total_operacoes', 0)}" f"🎯 Taxa de acerto: {stats.get('taxa_acerto', 0):.1f}%\n"
                
                f"{'='*30}\n"
                f"📊 Pesos do ensemble:\n"
                f"   🌲 Random Forest: {rede.ensemble.pesos_ensemble.get('random_forest', 0)*100:.1f}%" f"   📈 Gradient Boosting: {rede.ensemble.pesos_ensemble.get('gradient_boosting', 0)*100:.1f}%\n"
                f"   ⚡ XGBoost: {rede.ensemble.pesos_ensemble.get('xgboost', 0)*100:.1f}%" f"   🧠 LSTM: {rede.ensemble.pesos_ensemble.get('lstm', 0)*100:.1f}%" )

        #melhor_entrada_label.config(text=f"Melhor estr: {ANALISE_ESTRATEGIA}")



        
        atualizar_job = root.after(10000, atualizar_tabela)
        
        avisos = ["FECHAR OPERACAO", "RETORNAR OPERACAO" , "MUDOU", "QUEBROU","CAVEIRA_P*"]
                   
        #for ALERTA_ATUAL in avisos:
        #    if aviso in texto:
        #        ALERTA_ATUAL = aviso
        #        ATIVO_COM_ALERTA = prefixo
        #        break

        if ALERTA_ATUAL == "CAVEIRA":
            alerta_label.config(text=F"☠️ CAVEIRA DETECTADA {ATIVO_COM_ALERTA}", bg="red")
        elif ALERTA_ATUAL == "HULL":
            alerta_label.config(text=F"🚀 HULL DETECTADO {ATIVO_COM_ALERTA}", bg="blue")
        elif ALERTA_ATUAL in avisos:
            alerta_label.config(text=F"🚀 {ALERTA_ATUAL} {ATIVO_COM_ALERTA}", bg="green")
        
        
        else:
            alerta_label.config(text="", bg="black")

         

    def atualizar_tabela_obs():
        nonlocal atualizar_obs_job
        for i in tree_obs.get_children():
            tree_obs.delete(i)
        for ativo, dados in OBSERVAR.items():
            preco = preco_medio(ativo)
            if preco:
                status = dados.get("status", "indefinido")
                intens= dados.get("intensidade", "0.0")
                int_geral= dados.get("int_geral", "0.0")
                N_reset=dados.get("reset", "0.0")
                tree_obs.insert("", "end", values=(
                    ativo, f"{dados['preco_inicial']:.2f}", f"{preco:.2f}",N_reset,status, intens, int_geral
                ))
        atualizar_obs_job = root.after(10000, atualizar_tabela_obs)

    def atualizar_imagem():
        if ULTIMA_IMAGEM and os.path.exists(ULTIMA_IMAGEM):
            try:
                pil_img = Image.open(ULTIMA_IMAGEM)
                pil_img = pil_img.resize((800, 240))
                tk_img = ImageTk.PhotoImage(pil_img)
                img_label.config(image=tk_img, text="")
                img_label.image = tk_img
                legenda_label.config(text=f"📸 {ULTIMA_IMAGEM_NOME}" if ULTIMA_IMAGEM_NOME else "📸 imagem recebida")
                
            except Exception as e:
                print("⚠️ Erro ao carregar imagem:", e)
        root.after(10000, atualizar_imagem)

        
    # Inicializa atualizações
    atualizar_tabela()
    atualizar_tabela_obs()
    atualizar_imagem()
    root.mainloop()


# --- Loop principal assíncrono ---
async def main():
    await asyncio.gather(
        checar_mensagens(),
        enviar_arquivos_mt5(),
        monitorar_ativos()
    )

def iniciar_bot():
    asyncio.run(main())

if __name__ == "__main__":
    threading.Thread(target=iniciar_bot, daemon=True).start()
    iniciar_gui()

