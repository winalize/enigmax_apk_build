# codec.py
# Remote config oran encode/decode aracı
# Encode: encoded = round(oran * 100) + 200
# Decode: decoded = (encoded - 200) / 100

def encode_odd(odd):
    return round(float(odd) * 100) + 200

def decode_odd(encoded):
    return (int(encoded) - 200) / 100

if __name__ == "__main__":
    print("eNigMax Remote Config Codec")
    print("1) Oran encode")
    print("2) Encoded decode")
    choice = input("Seçim: ").strip()

    if choice == "1":
        odd = input("Normal oran girin örn 1.25: ").strip().replace(",", ".")
        print(encode_odd(odd))
    elif choice == "2":
        encoded = input("Encoded değer girin örn 325: ").strip()
        print(decode_odd(encoded))
    else:
        print("Geçersiz seçim")
