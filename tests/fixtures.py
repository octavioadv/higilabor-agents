"""
Mock outputs reutilizáveis nos testes.
"""
import json

MOCK_DEPOIMENTOS_OUTPUT = json.dumps(
    {
        "mensagem_solicitacao": "Olá, gostaríamos de compartilhar sua experiência.",
        "roteiro_perguntas": [
            "Qual problema enfrentava antes?",
            "Como a Higilabor ajudou?",
            "Qual resultado concreto?",
            "Recomendaria a outros?",
            "Algo mais a acrescentar?",
        ],
        "depoimento_curto": "A Higilabor transformou nossa gestão de SST.",
        "depoimento_expandido": "Antes da Higilabor, nossa documentação era desorganizada. "
        "Após a implementação do PGR e LTCAT, alcançamos conformidade total.",
        "cta_sugerido": "Conheça os serviços da Higilabor",
        "hashtags": ["#SST", "#Higilabor", "#SegurançaDoTrabalho"],
    },
    ensure_ascii=False,
)

MOCK_ORCHESTRATOR_OUTPUT = json.dumps(
    {
        "plano_execucao": [
            {
                "ordem": 1,
                "agente": "01-depoimentos",
                "objetivo": "Coletar depoimentos de clientes ativos",
                "insumos": ["lista de clientes", "template de perguntas"],
                "prazo_dias": 15,
            },
            {
                "ordem": 2,
                "agente": "02-cases",
                "objetivo": "Documentar casos de sucesso",
                "insumos": ["depoimentos coletados"],
                "prazo_dias": 15,
            },
        ],
        "criterios_sucesso": [
            "Mínimo 3 depoimentos coletados",
            "2 cases publicados no site",
        ],
        "dependencias": ["02-cases depende de 01-depoimentos"],
        "resumo_executivo": "Plano de teste com 2 etapas sequenciais.",
    },
    ensure_ascii=False,
)
