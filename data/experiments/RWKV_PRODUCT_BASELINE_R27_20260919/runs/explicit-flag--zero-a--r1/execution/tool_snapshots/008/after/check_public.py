from flags import enabled

def check_public():
    assert enabled('true') == True
    assert enabled('false') == False
    assert enabled(' NO ') == False
    print("all checks passed")

if __name__ == "__main__":
    check_public()
