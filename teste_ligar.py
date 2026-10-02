# from pyrogram import Client
# from pytgcalls import PyTgCalls

# app = Client('minha_sessao')
# call_py = PyTgCalls(app)

# @app.on_message(filters.command('call'))
# async def call_command(_, message):
#     # Inicia uma chamada e reproduz um arquivo de áudio
#     await call_py.play(
#         message.chat.id,  # ou o ID do usuário destino
#         'caminho/para/seu_audio.raw'  # ou URL de um arquivo
#     )


import asyncio
from pyrogram import Client
from pytgcalls import PyTgCalls


API_ID = "@Minhasopcoes"          # Substitua pelo seu API_ID
API_HASH = "2093745787:AAEDZew3QqB6eMQEZwjcFxo22TU_PL74i-s"  # Substitua pelo seu API_HASH

app = Client("sessao", api_id=API_ID, api_hash=API_HASH)
call_py = PyTgCalls(app)

async def main():
    await app.start()
    await call_py.start()
    print("Tudo certo!")
    await asyncio.Event().wait()

asyncio.run(main())


# import os
# import asyncio
# import tempfile
# import math
# import struct
# from pyrogram import Client, filters
# from pyrogram.types import Message
# from pytgcalls import PyTgCalls
# from pytgcalls.types import AudioParameters, AudioQuality

# # ================= CONFIGURAÇÕES =================
# API_ID = "@Minhasopcoes"          # Substitua pelo seu API_ID
# API_HASH = "2093745787:AAEDZew3QqB6eMQEZwjcFxo22TU_PL74i-s"  # Substitua pelo seu API_HASH

# # Inicializa o cliente Pyrogram (sessão do USUÁRIO, não bot)
# app = Client(
#     "minha_sessao",      # Nome do arquivo de sessão (será criado)
#     api_id=API_ID,
#     api_hash=API_HASH,
# )

# # Inicializa o gerenciador de chamadas VoIP
# call_py = PyTgCalls(app)
# # =================================================


# def gerar_tom_raw(freq=440, duracao=3, taxa_amostragem=48000):
#     """
#     Gera um tom senoidal (nota musical) e salva como arquivo .raw (PCM 16-bit).
#     Retorna o caminho do arquivo temporário.
#     """
#     arquivo_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".raw")
#     try:
#         num_amostras = int(taxa_amostragem * duracao)
#         for i in range(num_amostras):
#             # Calcula o valor da onda senoidal
#             valor = int(32767 * math.sin(2 * math.pi * freq * i / taxa_amostragem))
#             # Empacota como signed 16-bit little-endian (formato exigido pelo pytgcalls)
#             dados = struct.pack('<h', valor)
#             arquivo_temp.write(dados)
#         arquivo_temp.close()
#         return arquivo_temp.name
#     except Exception as e:
#         arquivo_temp.close()
#         os.unlink(arquivo_temp.name)
#         raise e


# @app.on_message(filters.command("call") & filters.private)
# async def comando_chamada(client: Client, message: Message):
#     """
#     Quando o usuário enviar /call no chat privado:
#     - Gera um tom de 440Hz (Lá)
#     - Faz uma chamada de voz para o próprio usuário (ou para quem ele respondeu)
#     - Toca o tom e depois desliga.
#     """
#     # Define o destino: se respondeu a alguém, chama aquela pessoa; senão, chama quem enviou o comando
#     if message.reply_to_message:
#         destino_id = message.reply_to_message.from_user.id
#     else:
#         destino_id = message.chat.id  # No privado, é o próprio usuário

#     # 1) Gera o arquivo de áudio com a nota (3 segundos de 440Hz)
#     caminho_audio = gerar_tom_raw(freq=440, duracao=3, taxa_amostragem=48000)

#     try:
#         await message.reply_text(f"🔊 Ligando para {destino_id} com um tom de 440Hz...")

#         # 2) Inicia a chamada de voz
#         await call_py.start_call(
#             destino_id,
#             audio_parameters=AudioParameters(
#                 bitrate=AudioQuality.HIGH.bitrate,
#             )
#         )

#         # 3) Reproduz o áudio (a nota) durante a chamada
#         await call_py.play(
#             destino_id,
#             caminho_audio,
#             audio_parameters=AudioParameters(
#                 bitrate=AudioQuality.HIGH.bitrate,
#             )
#         )

#         # 4) Aguarda o tempo da nota (3s) + uma pequena margem
#         await asyncio.sleep(4)

#         # 5) Encerra a chamada
#         await call_py.leave_call(destino_id)
#         await message.reply_text("✅ Chamada encerrada.")

#     except Exception as e:
#         await message.reply_text(f"❌ Erro: {e}")
#     finally:
#         # Limpeza: remove o arquivo temporário
#         if os.path.exists(caminho_audio):
#             os.unlink(caminho_audio)


# async def main():
#     # Inicia o cliente do usuário e o módulo de chamadas
#     await app.start()
#     await call_py.start()
#     print("🤖 Bot está rodando. Envie /call no chat privado para testar!")
#     await asyncio.Event().wait()  # Mantém o script rodando


# if __name__ == "__main__":
#     asyncio.run(main())