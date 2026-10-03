from engine import criterion

def test_missing_information_cap():
    x = criterion("Teste", 20, "sem informação", positive=20, missing=True)
    assert x["points"] <= 5

def test_negative_does_not_exceed_weight():
    x = criterion("Teste", 15, "evidência", positive=10, negative=20)
    assert x["points"] == 0

if __name__ == "__main__":
    test_missing_information_cap()
    test_negative_does_not_exceed_weight()
    print("OK")
