import os
import pandas as pd
from playwright.sync_api import sync_playwright, Page
from dotenv import load_dotenv

# Carrega as variáveis do ficheiro .env para o ambiente
load_dotenv()

MAPA_SITUACAO = {
    "Brasileiro Maior": "1",
    "Brasileiro Adolescente": "4",
    "Brasileiro Criança": "2",
    "Estrangeiro": "3"
}

MAPA_DOCUMENTOS_BR_ADULTO = {
    "Carteira de Identidade": "1",
    "Carteira Profissional": "2",
    "Registro de Identificação Civil (RIC)": "7",
    "Carteira de Trabalho": "8",
    "Passaporte Brasileiro": "3",
    "Carteira Nacional de Habilitação (CNH)": "9",  # Chave atualizada para o novo padrão
    "Autorização de Viagem - FUNAI": "6",
    "CPF": "14"
}

MAPA_DOCUMENTOS_CRIANCA = {
    "Passaporte Brasileiro": "3",
    "Certidão de Nascimento": "5",
    "Carteira de Identidade": "1",
    "Autorização de Viagem (FUNAI)": "6",
    "CPF": "14"
}

MAPA_DOCUMENTOS_ESTRANGEIRO = {
    "Passaporte Estrangeiro": "10",
    "Cédula de Identidade de Estrangeiro (CIE)": "11",
    "Identidade diplomática ou consular": "12",
    "Outro documento legal de viagem": "13"
}

def fazer_login(pagina: Page, placa: str, nsolicitacao: str):
    """
    Realiza o login no sistema da ANTT e navega até a página de solicitações.
    """
    print("A aceder à página inicial...")
    pagina.goto("https://appweb1.antt.gov.br/autorizacaoDeViagem/AvPublico/inicial.asp")

    cnpj = os.getenv("CNPJ")
    codigo_acesso = os.getenv("CODIGO_ACESSO")

    # Verificação de segurança para garantir que as variáveis foram carregadas
    if not all([cnpj, codigo_acesso, placa, nsolicitacao]):
        print("ERRO CRÍTICO: Uma ou mais variáveis (CNPJ, CODIGO_ACESSO, PLACA_VEICULO, NUMERO_SOLICITACAO) não foram encontradas no ficheiro .env.")
        return None

    print("A preencher os dados de login...")
    pagina.locator('input[name="txtCNPJ"]').fill(cnpj)
    pagina.locator('input[name="txtPlacaVeiculo"]').fill(placa)
    pagina.locator('input[name="txtCodigoAcesso"]').fill(codigo_acesso)

    print("A entrar no sistema...")
    with pagina.expect_popup() as pagina2_info:
        pagina.get_by_role("button", name="Entrar").click()
    
    pagina2 = pagina2_info.value
    pagina2.wait_for_load_state("domcontentloaded")
    print("Login realizado com sucesso. A navegar para a autorização de viagem...")

    pagina2.get_by_role("link", name="Autorização de Viagem Comum").click()
    pagina2.get_by_role("row", name="Listar Solicitação/Autorizaçã").get_by_role("button").click()

    try:
        print(f"A procurar pela solicitação: {nsolicitacao}")
        pagina2.get_by_role("link", name=nsolicitacao).click()
    except Exception:
        print(f"ERRO: Solicitação '{nsolicitacao}' não foi encontrada na página.")
        print("Verifique o NUMERO_SOLICITACAO no ficheiro .env ou se a solicitação existe.")
        return None # Retorna None para parar a execução
    pagina2.get_by_role("button", name="Submit").nth(1).click()
    
    pagina2.goto("https://appweb1.antt.gov.br/autorizacaoDeViagem/AvPublico/relacao.asp")
    print("Página de inclusão de passageiros carregada.")
    
    return pagina2

def adicionar_passageiros(pagina: Page, caminho_csv: str):
    """
    Adiciona os passageiros a partir de um ficheiro CSV, usando lógica para
    selecionar as opções corretas de situação e tipo de documento.
    """
    try:
        # dtype=str força a leitura de todas as colunas como texto
        # .fillna('') substitui células vazias (NaN) por texto vazio, evitando o erro "nan"
        df_passageiros = pd.read_csv(caminho_csv, dtype=str).fillna('')
    except FileNotFoundError:
        print(f"ERRO: O ficheiro {caminho_csv} não foi encontrado.")
        return
    except KeyError as e:
        print(f"ERRO: Coluna {e} não encontrada no CSV. Verifique o cabeçalho do ficheiro.")
        return

    print(f"Encontrados {len(df_passageiros)} passageiros para adicionar.")

    for indice, passageiro in df_passageiros.iterrows():
        try:
            # --- 1. LÊ TODAS AS COLUNAS DO CSV PARA O PASSAGEIRO ATUAL ---
            nome = passageiro["nome"]
            situacao = passageiro["situacao"]
            crianca_de_colo = passageiro["crianca_de_colo"]
            tipo_documento = passageiro["tipo_documento"]
            numero_documento = passageiro["numero_documento"]
            orgao_expedidor = passageiro["orgao_expedidor"]
            ntelefone = passageiro["ntelefone"]
            
            print(f"A adicionar passageiro: {nome} (Situação: {situacao})")

            # --- 2. USA O DICIONÁRIO PARA SELECIONAR A SITUAÇÃO ---
            valor_situacao = MAPA_SITUACAO[situacao]
            pagina.locator("#cmbMotivoViagem").select_option(valor_situacao)

            # --- 3. ESCOLHE O DICIONÁRIO DE DOCUMENTOS CORRETO ---
            mapa_documentos_atual = None
            if situacao in ["Brasileiro Maior", "Brasileiro Adolescente"]:
                mapa_documentos_atual = MAPA_DOCUMENTOS_BR_ADULTO
            elif situacao == "Brasileiro Criança":
                mapa_documentos_atual = MAPA_DOCUMENTOS_CRIANCA
                if crianca_de_colo.lower() == 'sim':
                    print("   -> Marcando como criança de colo.")
                    pagina.locator("input[name=\"IdCriancaColo\"]").check()
            elif situacao == "Estrangeiro":
                mapa_documentos_atual = MAPA_DOCUMENTOS_ESTRANGEIRO
            
            # --- 4. PREENCHE O FORMULÁRIO USANDO A LÓGICA DINÂMICA ---
            valor_documento = mapa_documentos_atual[tipo_documento]
            seletor_documento_dinamico = f"#cmbTipoDocumento{valor_situacao}"
            
            pagina.locator('input[name="txtPassageiro"]').fill(nome)
            pagina.locator(seletor_documento_dinamico).select_option(valor_documento)
            pagina.locator('input[name="txtIdentidade"]').fill(numero_documento)
            pagina.locator('input[name="txtOrgao"]').fill(orgao_expedidor)
            pagina.locator("#telefone").fill(ntelefone)
        
            pagina.locator("#btnInc").click()
            pagina.wait_for_load_state("networkidle")

        except KeyError as e:
            print(f"  ERRO: Valor '{e}' não reconhecido para o passageiro '{nome}'. Verifique o CSV.")
            print("  Este passageiro foi ignorado. A continuar com o próximo...")
            pagina.reload()
            continue
        except Exception as e:
            print(f"  ERRO inesperado ao processar '{nome}': {e}")
            pagina.reload()
            continue

    print("Processo de adição de passageiros finalizado!")

def main():
    """
    Função principal que orquestra a automação.
    """
    # Lê todas as configurações do ficheiro .env
    placa_veiculo = os.getenv("PLACA_VEICULO")
    numero_solicitacao = os.getenv("NUMERO_SOLICITACAO")
    arquivo_passageiros = "passageiros.csv"

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=False)
        contexto = navegador.new_context()
        pagina_principal = contexto.new_page()

        try:
            pagina_passageiros = fazer_login(pagina_principal, placa_veiculo, numero_solicitacao)
            
            if pagina_passageiros:
                adicionar_passageiros(pagina_passageiros, arquivo_passageiros)
                print("Processo concluído. O navegador será fechado em 10 segundos.")
                pagina_passageiros.wait_for_timeout(10000)
            else:
                print("Não foi possível continuar devido a uma falha no login ou configuração.")

        except Exception as e:
            print(f"Ocorreu um erro durante a execução: {e}")
        finally:
            navegador.close()
            print("Navegador fechado.")

if __name__ == "__main__":
    main()
