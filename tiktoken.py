class _Enc:
    def encode(self, text):
        return text.split()

def get_encoding(name):
    return _Enc()
