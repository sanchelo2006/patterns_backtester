import json
from pathlib import Path
from src.config.settings import CANDLE_PATTERNS

# Create pattern descriptions
pattern_descriptions = {}

for pattern in CANDLE_PATTERNS:
    # Create basic description based on pattern name
    name_clean = pattern.replace('CDL', '').lower()

    # Determine pattern characteristics
    if 'DOJI' in pattern:
        category = 'Indecision/Reversal'
        direction = 'Neutral'
        components = 1
    elif 'HAMMER' in pattern or 'HANGINGMAN' in pattern:
        category = 'Reversal'
        direction = 'Both' if 'INVERTED' in pattern else 'Bullish' if 'HAMMER' in pattern else 'Bearish'
        components = 1
    elif 'ENGULFING' in pattern:
        category = 'Reversal'
        direction = 'Both'
        components = 2
    elif 'STAR' in pattern:
        category = 'Reversal'
        direction = 'Bullish' if 'MORNING' in pattern else 'Bearish' if 'EVENING' in pattern else 'Both'
        components = 3
    elif 'MARUBOZU' in pattern:
        category = 'Momentum'
        direction = 'Both'
        components = 1
    elif 'HARAMI' in pattern:
        category = 'Reversal'
        direction = 'Both'
        components = 2
    elif 'CROWS' in pattern:
        category = 'Reversal'
        direction = 'Bearish'
        components = 3
    elif 'SOLDIERS' in pattern:
        category = 'Reversal'
        direction = 'Bullish'
        components = 3
    else:
        category = 'Technical'
        direction = 'Both'
        components = 1

    pattern_descriptions[pattern] = {
        "description": f"{pattern}: Japanese candlestick pattern for technical analysis.",
        "interpretation": "Trading signal based on price action analysis.",
        "reliability": "Medium",
        "category": category,
        "type": "Candlestick pattern",
        "direction": direction,
        "components": components
    }

# Save to file
output_path = Path(__file__).parent / 'src' / 'data' / 'pattern_descriptions.json'
output_path.parent.mkdir(exist_ok=True)

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(pattern_descriptions, f, indent=2, ensure_ascii=False)

print(f"Generated pattern descriptions for {len(pattern_descriptions)} patterns")
print(f"Saved to: {output_path}")