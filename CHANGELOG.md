# Changelog

## [2025-07-30] - SDK LangChain + Separação de Responsabilidades de Deploy
### ✅ Concluído
- **Interface LangChain**: SDK agora é 100% compatível com padrões LangChain
- **Nomenclaturas Corporativas**: `for_integration_tests()` → `for_testing()` 
- **Factory Methods**: Adicionados `for_production()` e `for_development()`
- **Métodos Consolidados**: Removidos duplicatas (run_llm, run_langchain, etc.)
- **Interface Principal**: `invoke()` e `ainvoke()` como métodos principais
- **Responsabilidades**: Produção restrita à esteira de CI/CD automática
- **Documentação**: Todos os READMEs atualizados para refletir a realidade
- **Compatibilidade**: Métodos legados mantidos com warnings de deprecação
- **Resultados**: 15/15 testes passando (100%) - Interface limpa e funcional

### 🔧 Mudanças Técnicas
- Removidos métodos redundantes: `run_llm()`, `run_langchain()`
- Consolidados métodos duplicados: `invoke_generic()`, `generate_text()`
- Adicionados factory methods corporativos com validações rigorosas
- Interface focada exclusivamente em compatibilidade LangChain
- Configuração de produção documentada como uso interno apenas

### 📚 Documentação Atualizada
- `README.md` principal atualizado com interface LangChain
- `bradax-sdk/README.md` modernizado com separação de responsabilidades
- `bradax-broker/README.md` atualizado para refletir interface LangChain
- `MIGRATION_GUIDE.md` criado para transição suave
- Exemplos atualizados para novos padrões corporativos
- Deprecation warnings para métodos legados

### 🚀 Governança Corporativa
- Testes em produção restritos à esteira de deploy automático
- Desenvolvedores direcionados para ambientes apropriados
- Configurações de produção claramente marcadas como uso interno
- Documentação reflete responsabilidades reais de cada ambiente

---
*Projeto: Bradax SDK - Interface LangChain Corporativa*
