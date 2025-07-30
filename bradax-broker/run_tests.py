"""
Script para executar testes organizados do sistema Bradax.
Executa testes em ordem lógica com dados reais da OpenAI.
"""
import os
import sys
import subprocess
import time
from pathlib import Path


class BradaxTestRunner:
    """Runner organizado para testes do sistema Bradax."""
    
    def __init__(self):
        self.broker_dir = Path(__file__).parent.parent
        self.sdk_dir = self.broker_dir.parent / "bradax-sdk"
        self.results = {}
    
    def check_environment(self):
        """Verificar se ambiente está configurado."""
        print("🔍 Verificando ambiente de teste...")
        
        # Verificar chave OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your-openai-api-key-here":
            print("❌ OPENAI_API_KEY não configurada ou inválida")
            print("   Configure no arquivo .env do broker antes de executar testes")
            return False
        
        if not openai_key.startswith("sk-"):
            print("❌ OPENAI_API_KEY tem formato inválido")
            return False
        
        print("✅ OPENAI_API_KEY configurada")
        
        # Verificar estrutura de testes
        required_dirs = [
            self.broker_dir / "tests",
            self.broker_dir / "tests" / "unit",
            self.broker_dir / "tests" / "integration", 
            self.broker_dir / "tests" / "end_to_end"
        ]
        
        for test_dir in required_dirs:
            if not test_dir.exists():
                print(f"❌ Diretório de teste não encontrado: {test_dir}")
                return False
        
        print("✅ Estrutura de testes configurada")
        
        # Verificar dependências
        try:
            import pytest
            import fastapi
            import openai
            print("✅ Dependências principais disponíveis")
        except ImportError as e:
            print(f"❌ Dependência não encontrada: {e}")
            print("   Execute: pip install -r requirements.txt")
            return False
        
        return True
    
    def run_test_category(self, category, test_path, description):
        """Executar categoria de testes."""
        print(f"\n🧪 {description}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Comando pytest
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "--disable-warnings",
            f"--junit-xml={self.broker_dir}/test_results_{category}.xml"
        ]
        
        try:
            # Executar testes
            result = subprocess.run(
                cmd,
                cwd=self.broker_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ {description} - PASSOU ({duration:.1f}s)")
                self.results[category] = {"status": "PASS", "duration": duration}
            else:
                print(f"❌ {description} - FALHOU ({duration:.1f}s)")
                print("STDOUT:", result.stdout[-500:] if result.stdout else "Nenhuma saída")
                print("STDERR:", result.stderr[-500:] if result.stderr else "Nenhum erro")
                self.results[category] = {"status": "FAIL", "duration": duration, "error": result.stderr}
        
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} - TIMEOUT (>5min)")
            self.results[category] = {"status": "TIMEOUT", "duration": 300}
        
        except Exception as e:
            print(f"💥 {description} - ERRO: {e}")
            self.results[category] = {"status": "ERROR", "duration": 0, "error": str(e)}
    
    def run_all_tests(self):
        """Executar todos os testes em ordem lógica."""
        print("🚀 Iniciando testes completos do sistema Bradax")
        print(f"📁 Diretório broker: {self.broker_dir}")
        print(f"📁 Diretório SDK: {self.sdk_dir}")
        
        if not self.check_environment():
            print("\n❌ Ambiente não configurado adequadamente")
            return False
        
        # Ordem lógica de execução dos testes
        test_sequence = [
            {
                "category": "unit_endpoints",
                "path": self.broker_dir / "tests" / "unit" / "test_endpoints.py",
                "description": "Testes Unitários - Endpoints Básicos"
            },
            {
                "category": "integration_langchain",
                "path": self.broker_dir / "tests" / "integration" / "test_langchain_real.py",
                "description": "Integração LangChain - Chamadas Reais OpenAI"
            },
            {
                "category": "integration_guardrails",
                "path": self.broker_dir / "tests" / "integration" / "test_guardrails_real.py",
                "description": "Integração Guardrails - Validação LLM Real"
            },
            {
                "category": "integration_telemetry",
                "path": self.broker_dir / "tests" / "integration" / "test_telemetry_real.py",
                "description": "Integração Telemetria - Coleta Real de Dados"
            },
            {
                "category": "e2e_sdk_integration",
                "path": self.broker_dir / "tests" / "end_to_end" / "test_sdk_integration.py",
                "description": "End-to-End - Integração SDK-Broker"
            },
            {
                "category": "e2e_complete_system",
                "path": self.broker_dir / "tests" / "end_to_end" / "test_complete_system.py",
                "description": "End-to-End - Sistema Completo"
            }
        ]
        
        # Se SDK existe, adicionar testes do SDK
        if self.sdk_dir.exists():
            test_sequence.append({
                "category": "sdk_standalone",
                "path": self.sdk_dir / "tests" / "test_sdk_real.py",
                "description": "SDK - Testes Standalone"
            })
        
        # Executar sequência de testes
        total_start = time.time()
        
        for test_config in test_sequence:
            if test_config["path"].exists():
                self.run_test_category(
                    test_config["category"],
                    test_config["path"],
                    test_config["description"]
                )
            else:
                print(f"⚠️  Arquivo de teste não encontrado: {test_config['path']}")
                self.results[test_config["category"]] = {"status": "SKIP", "duration": 0}
        
        total_duration = time.time() - total_start
        
        # Relatório final
        self.print_final_report(total_duration)
        
        # Retornar sucesso se todos os testes essenciais passaram
        essential_tests = ["unit_endpoints", "integration_langchain", "integration_guardrails"]
        return all(self.results.get(test, {}).get("status") == "PASS" for test in essential_tests)
    
    def print_final_report(self, total_duration):
        """Imprimir relatório final dos testes."""
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO FINAL DOS TESTES")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.results.values() if r["status"] == "FAIL")
        skipped_tests = sum(1 for r in self.results.values() if r["status"] == "SKIP")
        
        print(f"📈 Total de categorias: {total_tests}")
        print(f"✅ Passou: {passed_tests}")
        print(f"❌ Falhou: {failed_tests}")
        print(f"⚠️  Pulou: {skipped_tests}")
        print(f"⏱️  Tempo total: {total_duration:.1f}s")
        
        print("\n📋 Detalhes por categoria:")
        for category, result in self.results.items():
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌", 
                "SKIP": "⚠️",
                "TIMEOUT": "⏰",
                "ERROR": "💥"
            }.get(result["status"], "❓")
            
            duration = result.get("duration", 0)
            print(f"  {status_icon} {category}: {result['status']} ({duration:.1f}s)")
        
        # Status geral
        if failed_tests == 0:
            print("\n🎉 TODOS OS TESTES PASSARAM!")
            print("   Sistema Bradax validado com dados reais da OpenAI.")
        else:
            print(f"\n⚠️  {failed_tests} CATEGORIAS FALHARAM")
            print("   Revise os logs de erro acima para detalhes.")
        
        print("\n📁 Logs detalhados salvos em:")
        print(f"   {self.broker_dir}/test_results_*.xml")
    
    def run_specific_test(self, test_name):
        """Executar teste específico."""
        test_mapping = {
            "endpoints": ("unit_endpoints", "tests/unit/test_endpoints.py"),
            "langchain": ("integration_langchain", "tests/integration/test_langchain_real.py"),
            "guardrails": ("integration_guardrails", "tests/integration/test_guardrails_real.py"),
            "telemetry": ("integration_telemetry", "tests/integration/test_telemetry_real.py"),
            "sdk": ("e2e_sdk_integration", "tests/end_to_end/test_sdk_integration.py"),
            "e2e": ("e2e_complete_system", "tests/end_to_end/test_complete_system.py")
        }
        
        if test_name not in test_mapping:
            print(f"❌ Teste '{test_name}' não encontrado")
            print(f"   Testes disponíveis: {', '.join(test_mapping.keys())}")
            return False
        
        category, path = test_mapping[test_name]
        test_path = self.broker_dir / path
        
        if not test_path.exists():
            print(f"❌ Arquivo de teste não encontrado: {test_path}")
            return False
        
        if not self.check_environment():
            return False
        
        self.run_test_category(category, test_path, f"Teste Específico - {test_name}")
        
        return self.results.get(category, {}).get("status") == "PASS"


def main():
    """Função principal do script."""
    runner = BradaxTestRunner()
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        success = runner.run_specific_test(test_name)
    else:
        success = runner.run_all_tests()
    
    # Exit code baseado no resultado
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
