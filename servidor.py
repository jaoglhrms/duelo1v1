import asyncio
import websockets
import json
import os

# Banco de dados simplificado para o teste
bd = {
    "goku": {"nome": "Goku", "vida": 100, "energia": 50, "atq": 15, "def": 10, "mag": 35, "res": 15, "tecnica": "Kamehameha", "custo_tec": 20},
    "gojo": {"nome": "Satoru Gojo", "vida": 90, "energia": 60, "atq": 12, "def": 12, "mag": 40, "res": 25, "tecnica": "Vazio Roxo", "custo_tec": 30}
}

# Estado central do jogo
estado_jogo = {
    "j1": bd["goku"].copy(),
    "j2": bd["gojo"].copy(),
    "turno": 1, # 1 para J1, 2 para J2
    "vencedor": None
}

conexoes = {} # Mapeia o websocket para "j1" ou "j2"

async def main():
    # O Render atribui uma porta através de uma variável de ambiente
    porta = int(os.environ.get("PORT", 8765))
    async with websockets.serve(gerenciar_batalha, "0.0.0.0", porta):
        print(f"Servidor a correr na porta {porta}. A aguardar lutadores...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

async def notificar_jogadores(log=""):
    mensagem = json.dumps({"tipo": "atualizacao", "estado": estado_jogo, "log": log})
    for conexao in conexoes.keys():
        await conexao.send(mensagem)

        

async def gerenciar_batalha(websocket):
    # Define quem é o jogador que acabou de entrar
    if "j1" not in conexoes.values():
        id_jogador = "j1"
    elif "j2" not in conexoes.values():
        id_jogador = "j2"
    else:
        await websocket.send(json.dumps({"tipo": "erro", "log": "A sala está cheia!"}))
        return

    conexoes[websocket] = id_jogador
    print(f"[{id_jogador}] Entrou na arena!")
    
    # Manda a identidade para o jogador e avisa a todos
    await websocket.send(json.dumps({"tipo": "identidade", "id": id_jogador}))
    await notificar_jogadores(f"{estado_jogo[id_jogador]['nome']} entrou na arena!")

    try:
        async for mensagem in websocket:
            dados = json.loads(mensagem)
            acao = dados.get("acao")
            
            # Verifica se o jogo já acabou ou se não é o turno do jogador
            if estado_jogo["vencedor"]:
                continue
                
            numero_jogador = 1 if id_jogador == "j1" else 2
            if estado_jogo["turno"] != numero_jogador:
                continue # Ignora o comando se não for a vez dele

            atacante = estado_jogo["j1"] if id_jogador == "j1" else estado_jogo["j2"]
            defensor = estado_jogo["j2"] if id_jogador == "j1" else estado_jogo["j1"]
            log_acao = ""

            # Lógica de combate processada no Back-end
            if acao == 'fisico':
                dano = max(1, atacante['atq'] - defensor['def'])
                defensor['vida'] -= dano
                log_acao = f"💥 {atacante['nome']} deu um ataque físico causando {dano} de dano!"
            
            elif acao == 'magico':
                if atacante['energia'] >= atacante['custo_tec']:
                    atacante['energia'] -= atacante['custo_tec']
                    dano = max(1, atacante['mag'] - defensor['res'])
                    defensor['vida'] -= dano
                    log_acao = f"✨ {atacante['nome']} usou {atacante['tecnica']} causando {dano} de dano!"
                else:
                    log_acao = f"❌ {atacante['nome']} falhou a magia por falta de energia!"
            
            elif acao == 'focar':
                atacante['energia'] += 20
                log_acao = f"🔋 {atacante['nome']} focou e recuperou 20 de energia."

            # Verifica se alguém morreu
            if defensor['vida'] <= 0:
                defensor['vida'] = 0
                estado_jogo["vencedor"] = atacante['nome']
                log_acao += f" 🏆 VITÓRIA DE {atacante['nome']}!"

            # Passa o turno
            estado_jogo["turno"] = 2 if estado_jogo["turno"] == 1 else 1
            
            # Avisa todo mundo do novo estado
            await notificar_jogadores(log_acao)

            

    finally:
        print(f"[{id_jogador}] Saiu da arena.")
        del conexoes[websocket]

async def main():
    async with websockets.serve(gerenciar_batalha, "localhost", 8765):
        print("Servidor rodando na porta 8765. Aguardando lutadores...")
        await asyncio.Future()

        

if __name__ == "__main__":
    asyncio.run(main())

    