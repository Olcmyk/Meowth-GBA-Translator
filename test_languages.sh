#!/bin/bash
# Test script for Latin-to-Latin language translation support

set -e

echo "=== Testing Language Support Implementation ==="
echo ""

# Test 1: Verify CLI accepts language parameters
echo "Test 1: Checking CLI help for language parameters..."
python -m meowth.cli translate --help | grep -q "source" && echo "✓ --source parameter exists"
python -m meowth.cli translate --help | grep -q "target" && echo "✓ --target parameter exists"
python -m meowth.cli build --help | grep -q "source" && echo "✓ build command has --source"
python -m meowth.cli build --help | grep -q "target" && echo "✓ build command has --target"
echo ""

# Test 2: Verify language validation
echo "Test 2: Testing language validation..."
python -c "from meowth.languages import validate_language; validate_language('en'); print('✓ English validated')"
python -c "from meowth.languages import validate_language; validate_language('es'); print('✓ Spanish validated')"
python -c "from meowth.languages import validate_language; validate_language('fr'); print('✓ French validated')"
python -c "from meowth.languages import validate_language; validate_language('de'); print('✓ German validated')"
python -c "from meowth.languages import validate_language; validate_language('it'); print('✓ Italian validated')"
python -c "from meowth.languages import validate_language; validate_language('pt-BR'); print('✓ Portuguese validated')"
python -c "from meowth.languages import validate_language; validate_language('zh-Hans'); print('✓ Chinese validated')"
echo ""

# Test 3: Verify CJK detection
echo "Test 3: Testing CJK language detection..."
python -c "from meowth.languages import is_cjk_language; assert is_cjk_language('zh-Hans'); print('✓ Chinese is CJK')"
python -c "from meowth.languages import is_cjk_language; assert not is_cjk_language('es'); print('✓ Spanish is not CJK')"
python -c "from meowth.languages import is_cjk_language; assert not is_cjk_language('en'); print('✓ English is not CJK')"
echo ""

# Test 4: Verify Glossary initialization
echo "Test 4: Testing Glossary with different language pairs..."
python -c "from meowth.glossary import Glossary; g = Glossary(source_lang='en', target_lang='es'); print('✓ EN→ES glossary created')"
python -c "from meowth.glossary import Glossary; g = Glossary(source_lang='en', target_lang='zh-Hans'); print('✓ EN→ZH glossary created')"
echo ""

# Test 5: Verify Translator initialization
echo "Test 5: Testing Translator with different languages..."
python -c "from meowth.translator import Translator; t = Translator(source_lang='en', target_lang='es'); print('✓ EN→ES translator created')"
python -c "from meowth.translator import Translator; t = Translator(source_lang='en', target_lang='zh-Hans'); print('✓ EN→ZH translator created')"
echo ""

# Test 6: Verify Charmap with language parameter
echo "Test 6: Testing Charmap with target language..."
python -c "from meowth.charmap import Charmap; c = Charmap(target_lang='es'); print('✓ Charmap for Spanish created')"
python -c "from meowth.charmap import Charmap; c = Charmap(target_lang='zh-Hans'); print('✓ Charmap for Chinese created')"
echo ""

# Test 7: Verify Pipeline initialization
echo "Test 7: Testing Pipeline with language parameters..."
python -c "from meowth.pipeline import Pipeline; p = Pipeline(source_lang='en', target_lang='es'); print('✓ EN→ES pipeline created')"
python -c "from meowth.pipeline import Pipeline; p = Pipeline(source_lang='en', target_lang='zh-Hans'); print('✓ EN→ZH pipeline created')"
python -c "from meowth.pipeline import Pipeline; p = Pipeline(); print('✓ Default pipeline (backward compatibility) created')"
echo ""

# Test 8: Verify character replacements
echo "Test 8: Testing Portuguese character replacements..."
python -c "from meowth.languages import postprocess_for_language; result = postprocess_for_language('São Paulo', 'pt-BR'); assert 'ã' not in result; print('✓ Portuguese ã replaced')"
python -c "from meowth.languages import postprocess_for_language; result = postprocess_for_language('Pokémon', 'es'); print('✓ Spanish text processed')"
echo ""

echo "=== All tests passed! ==="
echo ""
echo "Next steps for manual testing:"
echo "1. Test backward compatibility (Chinese translation):"
echo "   meowth extract testgba/emerald_en.gba -o work/texts.json"
echo "   meowth translate work/texts.json -o work/texts_translated.json"
echo "   meowth build testgba/emerald_en.gba --translations work/texts_translated.json -o outputs/emerald_cn.gba"
echo ""
echo "2. Test Latin-to-Latin translation (Spanish):"
echo "   meowth extract testgba/firered_en.gba -o work/texts.json --source en --target es"
echo "   meowth translate work/texts.json --source en --target es -o work/texts_es.json"
echo "   meowth build testgba/firered_en.gba --translations work/texts_es.json --source en --target es -o outputs/firered_es.gba"
echo ""
echo "3. Verify in emulator:"
echo "   - Font patch should be skipped for Spanish (check console output)"
echo "   - Text should display correctly without font corruption"
echo "   - Accented characters should render properly"
