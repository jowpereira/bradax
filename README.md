# bradax SDK & Broker

**Runtime de IA generativa seguro e flexível para a Bradesco Seguros**

---

## 1 • Visão Geral

`bradax` é o **SDK oficial em Python** e o *broker* de execução que conecta times internos, parceiros e turmas de treinamento ao **Gen‑AI Hub** da Bradesco Seguros.
Ele encapsula a complexidade da orquestração de LLMs, construção de grafos e gerenciamento de infraestrutura, permitindo que você concentre esforço na lógica de negócio.

> **Destaques**
>
> * Tokens curtos por projeto, sem exposição de segredos.
> * Builder API para criar grafos em poucas linhas **ou** importar grafos LangGraph completos para customização total.
> * Biblioteca de **agentes prontos** (RAG, CRAG, SQL, DataFrame, ChatOps).
> * Observabilidade, rastreabilidade e controle de custos centralizados.

---

## 2 • Componentes da Plataforma

| Camada            | Função                                                                                                                               | Tecnologias                                         |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| **bradax‑sdk**    | Pacote PyPI com dois modos de uso<br>• `Full()` – ilimitado para squads de produto<br>• `Student()` – limitado a 30 req/min, sandbox | Python 3.12 • LangChain ≥ 0.10 • Pydantic • AsyncIO |
| **Graph Builder** | DSL e parser YAML que convertem definições declarativas em grafos LangGraph                                                          | NetworkX • Jinja2                                   |
| **Agent Library** | Conjunto de agentes parametrizáveis (RAGAgent, CRAGAgent, SQLAgent, etc.) prontos para uso                                           | LangGraph • OpenAI Functions                        |
| **bradax‑broker** | Proxy gRPC + HTTP que injeta segredos e roteia chamadas de LLM/DB                                                                    | FastAPI • gRPC • OAuth 2.1                          |
| **Secret‑Vault**  | HSM + política de acesso com *audit trail*                                                                                           | HashiCorp Vault • AWS KMS                           |
| **Control‑Plane** | UI + API para provisionamento de projetos, emissão de tokens, quotas e métricas                                                      | React • tRPC • Postgres                             |

---

Este repositório foi iniciado em 25 de julho de 2025.
