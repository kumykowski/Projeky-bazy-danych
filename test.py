import barcode
from barcode.writer import ImageWriter

def test_barcode():
    barcode_class = barcode.get_barcode_class('code128')
    my_barcode = barcode_class('1234567890', writer=ImageWriter())
    filename = my_barcode.save("test_barcode")
    print("Kod kreskowy został zapisany jako:", filename)

test_barcode()
