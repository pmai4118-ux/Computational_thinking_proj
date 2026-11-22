from source.service.providers.geminiInterpreter import GeminiInterpreter
from source.service.providers.gemini_provider import GeminiProvider


def testLegacyInterpreterNameUsesSingleProviderImplementation():
    assert GeminiInterpreter is GeminiProvider
