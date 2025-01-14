from coinark_collector import CoinArkCollector
import json

def test_api_response():
    collector = CoinArkCollector()
    
    # Test funding rate
    print("\nTesting funding rate:")
    response = collector._make_request('fundingRate/current', {'type': 'current'})
    print(json.dumps(response, indent=2))
    
    # Test open interest
    print("\nTesting open interest:")
    response = collector._make_request('openInterest/v2/chart', {
        'baseCoin': 'BTC',
        'interval': '1h',
        'size': 10
    })
    print(json.dumps(response, indent=2))
    
    # Test liquidations
    print("\nTesting liquidations:")
    response = collector._make_request('liquidation/allExchange/intervals', {
        'baseCoin': 'BTC',
        'interval': '1h',
        'size': 10
    })
    print(json.dumps(response, indent=2))
    
    # Test market depth
    print("\nTesting market depth:")
    response = collector._make_request('market/depth', {
        'symbol': 'BTCUSDT',
        'limit': 5
    })
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    test_api_response()
