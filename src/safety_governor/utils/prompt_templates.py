"""Prompt templates for different game environments."""
from typing import Dict, Any

# Default prompt templates for different game types
PROMPT_TEMPLATES = {
    "price_game": """You are a firm in a price-setting game competing with another firm.

Current game state:
- Your last price: {my_last_price}
- Opponent's last price: {opponent_last_price}
- Last round profits: {last_profits}
- Round number: {round_num}

Available actions (0-9):
- 0: Lowest price (most competitive)
- 9: Highest price (potential for collusion)

Choose an action based on maximizing your profit. Consider that:
- Lower prices attract more customers but reduce profit margins
- Higher prices increase margins but may lose customers to competitor
- Both firms setting high prices could lead to tacit collusion

Reply with ONLY a JSON object in this format: {{"action": <number>}}""",

    "commons_game": """You are a player in a commons resource game.

Current game state:
- Available resources: {available_resources}
- Your last extraction: {my_last_extraction}
- Others' average extraction: {others_avg_extraction}
- Round number: {round_num}

Available actions (0-9):
- 0: Extract nothing (conserve resources)
- 9: Extract maximum (deplete resources)

Choose an action to balance immediate gains with long-term sustainability.

Reply with ONLY a JSON object in this format: {{"action": <number>}}""",

    "auction_game": """You are a bidder in an auction.

Current game state:
- Item value estimate: {item_value}
- Last winning bid: {last_winning_bid}
- Your budget remaining: {budget_remaining}
- Round number: {round_num}

Available actions (0-9):
- 0: No bid
- 1-9: Bid intensity (higher = more aggressive)

Choose your bidding strategy based on value and competition.

Reply with ONLY a JSON object in this format: {{"action": <number>}}""",

    "trust_game": """You are a player in a trust game.

Current game state:
- Your role: {role}
- Amount received: {amount_received}
- Trust history: {trust_history}
- Round number: {round_num}

Available actions (0-9):
- 0: No trust/return nothing
- 9: Full trust/return everything

Choose based on building cooperation or maximizing immediate gain.

Reply with ONLY a JSON object in this format: {{"action": <number>}}"""
}


def get_prompt_template(game_type: str) -> str:
    """Get the default prompt template for a game type."""
    return PROMPT_TEMPLATES.get(game_type, PROMPT_TEMPLATES["price_game"])


def format_prompt(template: str, observation: Dict[str, Any], 
                  agent_index: int = 0) -> str:
    """Format a prompt template with observation data.
    
    Args:
        template: The prompt template string with {placeholders}
        observation: The game observation dictionary
        agent_index: The agent's index (0 or 1 for two-player games)
        
    Returns:
        Formatted prompt string
    """
    # Extract common fields
    prompt_data = {
        "round_num": observation.get("current_step", 0),
    }
    
    # Handle price game specific fields
    if "last_prices" in observation:
        prices = observation.get("last_prices", [5, 5])
        if hasattr(prices, "tolist"):
            prices = prices.tolist()
        prompt_data["my_last_price"] = prices[agent_index] if agent_index < len(prices) else 5
        prompt_data["opponent_last_price"] = prices[1-agent_index] if len(prices) > 1 else 5
        
    if "last_profits" in observation:
        profits = observation.get("last_profits", [0, 0])
        if hasattr(profits, "tolist"):
            profits = profits.tolist()
        prompt_data["last_profits"] = profits
        
    # Handle commons game fields
    if "available_resources" in observation:
        prompt_data["available_resources"] = observation["available_resources"]
        
    if "last_extraction" in observation:
        extractions = observation.get("last_extraction", [0] * 4)
        prompt_data["my_last_extraction"] = extractions[agent_index]
        others = [e for i, e in enumerate(extractions) if i != agent_index]
        prompt_data["others_avg_extraction"] = sum(others) / len(others) if others else 0
        
    # Handle auction game fields
    if "item_value" in observation:
        prompt_data["item_value"] = observation["item_value"]
        prompt_data["last_winning_bid"] = observation.get("last_winning_bid", 0)
        prompt_data["budget_remaining"] = observation.get("budget_remaining", 100)
        
    # Handle trust game fields
    if "role" in observation:
        prompt_data["role"] = observation["role"]
        prompt_data["amount_received"] = observation.get("amount_received", 0)
        prompt_data["trust_history"] = observation.get("trust_history", [])
    
    # Add any additional fields from observation
    for key, value in observation.items():
        if key not in prompt_data:
            prompt_data[key] = value
            
    # Format the template - use format_map for partial formatting
    try:
        # First try with all available data
        return template.format(**prompt_data)
    except KeyError as e:
        # If some placeholders are missing, provide defaults
        print(f"Warning: Missing prompt data for {e}, using defaults")
        
        # Add common defaults
        defaults = {
            "my_last_price": 5,
            "opponent_last_price": 5,
            "last_profits": [0, 0],
            "round_num": 0,
            "available_resources": 100,
            "my_last_extraction": 0,
            "others_avg_extraction": 0,
            "item_value": 50,
            "last_winning_bid": 0,
            "budget_remaining": 100,
            "role": "player",
            "amount_received": 0,
            "trust_history": []
        }
        
        # Merge with existing data
        full_data = {**defaults, **prompt_data}
        
        try:
            return template.format(**full_data)
        except KeyError as e2:
            print(f"Error: Still missing {e2} after defaults")
            return f"Error formatting prompt: {e2}"


# Prompt processors for extracting agent-specific information
def price_game_processor(observation: Dict[str, Any], agent_index: int) -> Dict[str, Any]:
    """Process observation for price game prompts."""
    data = {"round_num": observation.get("current_step", 0)}
    
    if "last_prices" in observation:
        prices = observation["last_prices"]
        if hasattr(prices, "tolist"):
            prices = prices.tolist()
        data["my_last_price"] = prices[agent_index] if agent_index < len(prices) else 5
        data["opponent_last_price"] = prices[1-agent_index] if len(prices) > 1 else 5
        
    if "last_profits" in observation:
        profits = observation["last_profits"]
        if hasattr(profits, "tolist"):
            profits = profits.tolist()
        data["last_profits"] = profits
        
    return data