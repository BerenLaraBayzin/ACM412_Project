"""
Zengin demo verisi: çok sayıda kategori, kullanıcı, gerçek kitap ve kapak.

Çalıştır:
    python manage.py rich_seed
    python manage.py rich_seed --keep   # mevcut veriyi koru, sadece ekle
    python manage.py rich_seed --no-covers   # Open Library'den kapak indirme

Open Library Covers API kullanılır: https://covers.openlibrary.org/
ISBN bilinen kitaplar için public domain kapak görselleri çekilir.
"""

import json
import os
import random
import textwrap
import urllib.request
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Book, Category, Message, Order


CATEGORIES = [
    ("Roman", "roman"),
    ("Felsefe", "felsefe"),
    ("Bilim & Teknoloji", "bilim-teknoloji"),
    ("Tarih", "tarih"),
    ("Şiir", "siir"),
    ("Polisiye", "polisiye"),
    ("Çocuk & Genç", "cocuk-genc"),
    ("Kişisel Gelişim", "kisisel-gelisim"),
]

# (title, author, isbn, category_slug, price, condition, description)
BOOKS = [
    # Roman
    ("1984", "George Orwell", "9780451524935", "roman", "85.00", "good",
     "Distopik klasik. Az okunmuş, kapağı yıpranmış değil."),
    ("Hayvan Çiftliği", "George Orwell", "9780451526342", "roman", "55.00", "new",
     "Cep baskı, neredeyse hiç açılmamış."),
    ("Suç ve Ceza", "Fyodor Dostoyevski", "9780486415871", "roman", "120.00", "good",
     "Ciltli baskı. İçeride önemli yerler işaretli (kurşunkalem)."),
    ("Karamazov Kardeşler", "Fyodor Dostoyevski", "9780374528379", "roman", "180.00", "good",
     "Çevirmen: Nihal Yalaza Taluy. İyi durumda."),
    ("Kürk Mantolu Madonna", "Sabahattin Ali", "9789754700565", "roman", "65.00", "new",
     "İletişim Yayınları, çok yeni."),
    ("Tutunamayanlar", "Oğuz Atay", "9789750802713", "roman", "210.00", "used",
     "Kült roman, kalın cilt. Kapak köşeleri yıpranmış."),
    ("Anna Karenina", "Lev Tolstoy", "9780143035008", "roman", "150.00", "good",
     "Penguin Classics, İngilizce. Aydınger sayfa ayracı dahil."),
    ("Yüzyıllık Yalnızlık", "Gabriel García Márquez", "9780060883287", "roman", "110.00", "good",
     "Büyülü gerçekçiliğin başyapıtı. Sayfa kıvrıkları az."),
    ("Sineklerin Tanrısı", "William Golding", "9780399501487", "roman", "75.00", "used",
     "Lise yıllarımdan kalma. Notlar var."),
    ("Otomatik Portakal", "Anthony Burgess", "9780393312836", "roman", "95.00", "good",
     "İngilizce orijinal baskı. Glossary dahil."),
    ("Beyaz Diş", "Jack London", "9781503215511", "roman", "45.00", "new",
     "Cep boy, hiç okunmamış gibi."),
    ("Bülbülü Öldürmek", "Harper Lee", "9780446310789", "roman", "90.00", "good",
     "Klasik Amerikan romanı. Kapağında küçük lekeler var."),

    # Felsefe
    ("Sofi'nin Dünyası", "Jostein Gaarder", "9780425152256", "felsefe", "130.00", "good",
     "Felsefeye giriş için klasik. Az notlu."),
    ("Böyle Buyurdu Zerdüşt", "Friedrich Nietzsche", "9780140441185", "felsefe", "100.00", "good",
     "Penguin Classics. Çok az altı çizili."),
    ("Devlet", "Platon", "9780872201361", "felsefe", "115.00", "used",
     "Cumhuriyet yayını. Yıpranmış ama tam."),
    ("Anlamın İzinde Yaşam", "Viktor Frankl", "9780807014295", "felsefe", "85.00", "new",
     "Logoterapinin temel kitabı, kullanılmamış gibi."),

    # Bilim & Teknoloji
    ("Zamanın Kısa Tarihi", "Stephen Hawking", "9780553380163", "bilim-teknoloji", "120.00", "good",
     "Türkçe baskı. Birkaç sayfa kıvrık."),
    ("Sapiens: Hayvanlardan Tanrılara", "Yuval Noah Harari", "9780062316097", "bilim-teknoloji", "140.00", "new",
     "Kolektif Kitap, neredeyse hiç açılmamış."),
    ("Bencil Gen", "Richard Dawkins", "9780198788607", "bilim-teknoloji", "110.00", "good",
     "Oxford baskı. Az altı çizili."),
    ("Clean Code", "Robert C. Martin", "9780132350884", "bilim-teknoloji", "350.00", "used",
     "Yazılım klasiği. Çalışırken çok kullandım, notlu."),
    ("Pragmatic Programmer", "Andrew Hunt & David Thomas", "9780201616224", "bilim-teknoloji", "300.00", "good",
     "İngilizce ilk baskı. İyi durumda."),
    ("Python Crash Course", "Eric Matthes", "9781593279288", "bilim-teknoloji", "220.00", "good",
     "Başlangıç düzeyi için harika. Tertemiz."),
    ("Introduction to Algorithms (CLRS)", "Cormen et al.", "9780262033848", "bilim-teknoloji", "650.00", "used",
     "Üçüncü baskı. Sırt biraz açık, içerik tamam."),

    # Tarih
    ("Nutuk", "Mustafa Kemal Atatürk", "9789753860451", "tarih", "150.00", "new",
     "Türk Tarih Kurumu baskı. Hiç açılmamış."),
    ("Osmanlı İmparatorluğu Klasik Çağ", "Halil İnalcık", "9789751607607", "tarih", "180.00", "good",
     "Türk tarihçiliğinin başyapıtlarından."),
    ("21. Yüzyıl İçin 21 Ders", "Yuval Noah Harari", "9781787330672", "tarih", "120.00", "new",
     "Çok yeni, hediye paketinden çıktı."),

    # Şiir
    ("Memleketimden İnsan Manzaraları", "Nazım Hikmet", "9789754700428", "siir", "85.00", "good",
     "YKY baskı. Sevdiğim şiirlerde sayfa katlı."),
    ("Sevda Sözleri", "Cemal Süreya", "9789750706103", "siir", "70.00", "new",
     "Toplu şiirler, küçük boy."),

    # Polisiye
    ("Doğu Ekspresinde Cinayet", "Agatha Christie", "9780062073631", "polisiye", "65.00", "good",
     "Klasik Christie. Sayfaları biraz sararmış."),
    ("Sherlock Holmes Bütün Maceraları", "Arthur Conan Doyle", "9780553212419", "polisiye", "200.00", "good",
     "Tek cilt, hepsi içinde. Kalın."),
    ("Kürk Mantolu Madonna'nın Sırrı", "Ahmet Ümit", "9789753428058", "polisiye", "75.00", "new",
     "Yeni baskı, neredeyse hiç açılmamış."),

    # Çocuk & Genç
    ("Şeker Portakalı", "José Mauro de Vasconcelos", "9789750714566", "cocuk-genc", "55.00", "good",
     "Klasik. Çocukluğumda okuduğum kopya."),
    ("Küçük Prens", "Antoine de Saint-Exupéry", "9780156012195", "cocuk-genc", "40.00", "new",
     "Resimli baskı, çok güzel durumda."),
    ("Hobbit", "J.R.R. Tolkien", "9780547928227", "cocuk-genc", "120.00", "good",
     "İngilizce, çocuk için ideal."),

    # Kişisel Gelişim
    ("Atomik Alışkanlıklar", "James Clear", "9780735211292", "kisisel-gelisim", "130.00", "new",
     "Tertemiz, ön kapakta hiç iz yok."),
    ("Düşünme Sanatı", "Rolf Dobelli", "9780062219695", "kisisel-gelisim", "95.00", "good",
     "Az notlu. Akıcı bir kitap."),
    ("Mindset", "Carol Dweck", "9780345472328", "kisisel-gelisim", "100.00", "good",
     "Türkçe çevirisi. İlk yarıda not var."),

    # --- Roman (ek) ---
    ("Sefiller", "Victor Hugo", "9780451419439", "roman", "175.00", "good",
     "İki cilt tek kitapta. Sırt sağlam, sayfalar temiz."),
    ("Don Kişot", "Miguel de Cervantes", "9780142437230", "roman", "160.00", "good",
     "Penguin Classics. Kapakta hafif yıpranma."),
    ("Savaş ve Barış", "Lev Tolstoy", "9781400079988", "roman", "220.00", "used",
     "Kalın cilt, çok okunmuş. Birkaç sayfa katlı."),
    ("Madame Bovary", "Gustave Flaubert", "9780140449129", "roman", "90.00", "good",
     "Penguin baskı. Az altı çizili."),
    ("Yeraltından Notlar", "Fyodor Dostoyevski", "9780679734529", "roman", "70.00", "good",
     "İnce kitap, tertemiz sayfalar."),
    ("Dönüşüm", "Franz Kafka", "9780553213690", "roman", "55.00", "new",
     "Cep baskı, hiç açılmamış gibi."),
    ("Dava", "Franz Kafka", "9780805209990", "roman", "85.00", "good",
     "İyi durumda, ön kapakta küçük kıvrım."),
    ("Yabancı", "Albert Camus", "9780679720201", "roman", "75.00", "new",
     "Vintage baskı, çok temiz."),
    ("Veba", "Albert Camus", "9780679720218", "roman", "95.00", "good",
     "Az notlu, akıcı çeviri."),
    ("Simyacı", "Paulo Coelho", "9780062315007", "roman", "80.00", "new",
     "HarperOne baskı, hediye gibi."),
    ("Gurur ve Önyargı", "Jane Austen", "9780141439518", "roman", "85.00", "good",
     "Penguin Classics. Kapak köşeleri hafif yıpranmış."),
    ("Jane Eyre", "Charlotte Brontë", "9780142437209", "roman", "95.00", "good",
     "Kalın cilt, sayfalar sararmaya başlamış."),
    ("Uğultulu Tepeler", "Emily Brontë", "9780141439556", "roman", "85.00", "good",
     "Klasik baskı, iyi durumda."),
    ("Frankenstein", "Mary Shelley", "9780141439471", "roman", "70.00", "new",
     "Penguin Classics, neredeyse hiç okunmamış."),
    ("Drakula", "Bram Stoker", "9780141439846", "roman", "90.00", "good",
     "Gotik klasik. Sayfa ayracı dahil."),
    ("Moby Dick", "Herman Melville", "9780142437247", "roman", "140.00", "used",
     "Büyük boy, sırt biraz açık. İçerik tam."),
    ("Çavdar Tarlasında Çocuklar", "J.D. Salinger", "9780316769488", "roman", "100.00", "good",
     "Klasik baskı. Az yıpranmış."),
    ("Cesur Yeni Dünya", "Aldous Huxley", "9780060850524", "roman", "95.00", "new",
     "Modern baskı, tertemiz."),
    ("Fahrenheit 451", "Ray Bradbury", "9781451673319", "roman", "85.00", "good",
     "Az altı çizili, akıcı."),
    ("Yaşlı Adam ve Deniz", "Ernest Hemingway", "9780684801223", "roman", "65.00", "new",
     "İnce kitap, kullanılmamış gibi."),
    ("Fareler ve İnsanlar", "John Steinbeck", "9780140177398", "roman", "60.00", "good",
     "Cep baskı. Birkaç sayfa kıvrık."),
    ("Gazap Üzümleri", "John Steinbeck", "9780143039433", "roman", "130.00", "good",
     "Penguin baskı, kalın. İyi durumda."),
    ("Genç Werther'in Acıları", "J.W. von Goethe", "9780140445039", "roman", "70.00", "good",
     "Klasik, az notlu."),
    ("İnce Memed", "Yaşar Kemal", "9789750806742", "roman", "120.00", "good",
     "YKY baskı. Sevdiğim bölümlerde sayfa katlı."),
    ("Saatleri Ayarlama Enstitüsü", "Ahmet Hamdi Tanpınar", "9789753638029", "roman", "110.00", "good",
     "Dergah Yayınları. Sırt sağlam."),
    ("Huzur", "Ahmet Hamdi Tanpınar", "9789753638005", "roman", "105.00", "good",
     "Dergah Yayınları, iyi durumda."),
    ("Aşk", "Elif Şafak", "9789752117761", "roman", "95.00", "new",
     "Doğan Kitap, çok yeni."),

    # --- Felsefe (ek) ---
    ("Düşünceler", "Marcus Aurelius", "9780140449334", "felsefe", "75.00", "good",
     "Stoacılığın temel metni. Penguin Classics."),
    ("Bir Stoacıdan Mektuplar", "Seneca", "9780140442106", "felsefe", "85.00", "good",
     "Az altı çizili, akıcı çeviri."),
    ("İyinin ve Kötünün Ötesinde", "Friedrich Nietzsche", "9780140449235", "felsefe", "90.00", "good",
     "Penguin Classics. Birkaç not var."),
    ("Ahlakın Soykütüğü", "Friedrich Nietzsche", "9780679724629", "felsefe", "85.00", "good",
     "Vintage baskı, iyi durumda."),
    ("Şölen", "Platon", "9780140449273", "felsefe", "70.00", "new",
     "İnce kitap, tertemiz."),
    ("Sokrates'in Son Günleri", "Platon", "9780140449280", "felsefe", "80.00", "good",
     "Penguin Classics. Az yıpranmış."),
    ("Nikomakhos'a Etik", "Aristoteles", "9780140449495", "felsefe", "110.00", "good",
     "Akademik baskı, dipnotlu."),
    ("Korku ve Titreme", "Søren Kierkegaard", "9780140444490", "felsefe", "85.00", "good",
     "Az notlu. Yoğun bir metin."),
    ("Bulantı", "Jean-Paul Sartre", "9780811220309", "felsefe", "80.00", "good",
     "New Directions baskı, iyi durumda."),
    ("Batı Felsefesi Tarihi", "Bertrand Russell", "9780671201586", "felsefe", "190.00", "used",
     "Kalın referans kitabı. Sırt açık ama tam."),

    # --- Bilim & Teknoloji (ek) ---
    ("Kozmos", "Carl Sagan", "9780345539434", "bilim-teknoloji", "150.00", "new",
     "Renkli baskı, çok temiz."),
    ("Soluk Mavi Nokta", "Carl Sagan", "9780345376596", "bilim-teknoloji", "120.00", "good",
     "Az altı çizili, akıcı."),
    ("Zarif Evren", "Brian Greene", "9780393338102", "bilim-teknoloji", "140.00", "good",
     "Sicim teorisine giriş. İyi durumda."),
    ("Gödel, Escher, Bach", "Douglas Hofstadter", "9780465026562", "bilim-teknoloji", "260.00", "used",
     "Kült kitap, kalın. Çok okunmuş, notlu."),
    ("Tüfek, Mikrop ve Çelik", "Jared Diamond", "9780393354324", "bilim-teknoloji", "160.00", "good",
     "Pulitzer ödüllü. Az notlu."),
    ("Homo Deus", "Yuval Noah Harari", "9780062464316", "bilim-teknoloji", "150.00", "new",
     "Kolektif Kitap. Tertemiz."),
    ("Büyük Sorulara Kısa Yanıtlar", "Stephen Hawking", "9781984819192", "bilim-teknoloji", "120.00", "new",
     "Son kitabı, hiç açılmamış gibi."),
    ("Refactoring", "Martin Fowler", "9780134757599", "bilim-teknoloji", "420.00", "good",
     "İkinci baskı. Yazılımcı klasiği, az notlu."),
    ("Design Patterns", "Erich Gamma et al. (GoF)", "9780201633610", "bilim-teknoloji", "380.00", "used",
     "Klasik GoF kitabı. Sırt yıpranmış."),
    ("The Mythical Man-Month", "Frederick Brooks", "9780201835953", "bilim-teknoloji", "260.00", "good",
     "Yazılım mühendisliği klasiği."),
    ("Code Complete", "Steve McConnell", "9780735619678", "bilim-teknoloji", "400.00", "good",
     "İkinci baskı. Kalın, iyi durumda."),
    ("Cracking the Coding Interview", "Gayle Laakmann McDowell", "9780984782857", "bilim-teknoloji", "300.00", "good",
     "Mülakat hazırlığı için. Az çözüm işaretli."),
    ("Fluent Python", "Luciano Ramalho", "9781492056355", "bilim-teknoloji", "450.00", "new",
     "İkinci baskı, tertemiz."),
    ("Eloquent JavaScript", "Marijn Haverbeke", "9781593279509", "bilim-teknoloji", "240.00", "good",
     "Üçüncü baskı. Az notlu."),
    ("Hands-On Machine Learning", "Aurélien Géron", "9781492032649", "bilim-teknoloji", "520.00", "good",
     "İkinci baskı. ML için referans."),

    # --- Tarih (ek) ---
    ("İpek Yolu: Dünyanın Yeni Tarihi", "Peter Frankopan", "9781101912379", "tarih", "170.00", "good",
     "Kapsamlı dünya tarihi. İyi durumda."),
    ("SPQR: Antik Roma Tarihi", "Mary Beard", "9781631492228", "tarih", "160.00", "new",
     "Çok beğenilen Roma tarihi. Tertemiz."),
    ("Ağustos Topları", "Barbara Tuchman", "9780345476098", "tarih", "140.00", "good",
     "I. Dünya Savaşı'nın başlangıcı. Az notlu."),
    ("Amerika'nın Halk Tarihi", "Howard Zinn", "9780062397348", "tarih", "150.00", "good",
     "Alternatif bir tarih anlatısı."),

    # --- Şiir (ek) ---
    ("Çimen Yaprakları", "Walt Whitman", "9780140421996", "siir", "90.00", "good",
     "Penguin Classics. Sevilen şiirlerde işaret var."),
    ("Özsel Rumi", "Mevlana Celaleddin Rumi", "9780062509581", "siir", "110.00", "new",
     "Coleman Barks çevirisi. Çok temiz."),
    ("Yirmi Aşk Şiiri ve Umutsuz Bir Şarkı", "Pablo Neruda", "9780143039969", "siir", "75.00", "new",
     "İki dilli baskı, tertemiz."),

    # --- Polisiye (ek) ---
    ("On Küçük Zenci", "Agatha Christie", "9780062073488", "polisiye", "70.00", "good",
     "Christie'nin başyapıtı. Sayfalar hafif sararmış."),
    ("Roger Ackroyd Cinayeti", "Agatha Christie", "9780062073563", "polisiye", "70.00", "good",
     "Klasik kıvrımlı kurgu. İyi durumda."),
    ("Nil'de Ölüm", "Agatha Christie", "9780062073556", "polisiye", "75.00", "new",
     "Poirot serisi. Çok temiz."),
    ("Baskerville'lerin Köpeği", "Arthur Conan Doyle", "9780140437867", "polisiye", "65.00", "good",
     "Sherlock Holmes klasiği. Az yıpranmış."),
    ("Malta Şahini", "Dashiell Hammett", "9780679722649", "polisiye", "80.00", "good",
     "Kara roman klasiği. İyi durumda."),
    ("Büyük Uyku", "Raymond Chandler", "9780394758282", "polisiye", "75.00", "good",
     "Philip Marlowe serisi. Az notlu."),
    ("Ejderha Dövmeli Kız", "Stieg Larsson", "9780307454546", "polisiye", "110.00", "good",
     "Millennium serisi 1. kitap. Kalın."),
    ("Da Vinci Şifresi", "Dan Brown", "9780307474278", "polisiye", "95.00", "good",
     "Robert Langdon serisi. Çok okunmuş ama sağlam."),
    ("Kayıp Kız", "Gillian Flynn", "9780307588371", "polisiye", "100.00", "new",
     "Gerilim. Neredeyse hiç açılmamış."),

    # --- Çocuk & Genç (ek) ---
    ("Harry Potter ve Felsefe Taşı", "J.K. Rowling", "9780747532699", "cocuk-genc", "140.00", "good",
     "Serinin ilk kitabı. Kapakta küçük iz."),
    ("Harry Potter ve Sırlar Odası", "J.K. Rowling", "9780747538493", "cocuk-genc", "140.00", "good",
     "İkinci kitap. İyi durumda."),
    ("Charlie'nin Çikolata Fabrikası", "Roald Dahl", "9780142410318", "cocuk-genc", "55.00", "new",
     "Resimli baskı, tertemiz."),
    ("Matilda", "Roald Dahl", "9780142410370", "cocuk-genc", "55.00", "new",
     "Quentin Blake çizimli. Çok güzel durumda."),
    ("Alice Harikalar Diyarında", "Lewis Carroll", "9780141439761", "cocuk-genc", "60.00", "good",
     "Penguin Classics. Az yıpranmış."),
    ("Peter Pan", "J.M. Barrie", "9780141322575", "cocuk-genc", "55.00", "good",
     "Puffin baskı, iyi durumda."),
    ("Define Adası", "Robert Louis Stevenson", "9780141321004", "cocuk-genc", "60.00", "good",
     "Macera klasiği. Birkaç sayfa kıvrık."),
    ("Açlık Oyunları", "Suzanne Collins", "9780439023528", "cocuk-genc", "110.00", "good",
     "Serinin ilk kitabı. Çok okunmuş ama sağlam."),
    ("Narnia: Aslan, Cadı ve Dolap", "C.S. Lewis", "9780064404990", "cocuk-genc", "70.00", "new",
     "Renkli kapak, tertemiz."),
    ("Yüzük Kardeşliği", "J.R.R. Tolkien", "9780547928210", "cocuk-genc", "150.00", "good",
     "Yüzüklerin Efendisi 1. kitap. İyi durumda."),

    # --- Kişisel Gelişim (ek) ---
    ("İnsanları Etkileme ve Dost Kazanma Sanatı", "Dale Carnegie", "9780671027032", "kisisel-gelisim", "90.00", "good",
     "Klasik. Az altı çizili."),
    ("Etkili İnsanların 7 Alışkanlığı", "Stephen Covey", "9780743269513", "kisisel-gelisim", "110.00", "good",
     "İş ve yaşam için klasik. İyi durumda."),
    ("Zengin Baba Yoksul Baba", "Robert Kiyosaki", "9781612680194", "kisisel-gelisim", "95.00", "new",
     "Finansal okuryazarlık. Tertemiz."),
    ("Hızlı ve Yavaş Düşünme", "Daniel Kahneman", "9780374533557", "kisisel-gelisim", "150.00", "good",
     "Davranışsal ekonomi klasiği. Az notlu."),
    ("Akış", "Mihaly Csikszentmihalyi", "9780061339202", "kisisel-gelisim", "100.00", "good",
     "Mutluluk psikolojisi. İyi durumda."),
    ("Sıfırdan Bire", "Peter Thiel", "9780804139298", "kisisel-gelisim", "120.00", "new",
     "Girişimcilik üzerine. Hiç açılmamış gibi."),
    ("Etki: İkna Psikolojisi", "Robert Cialdini", "9780061241895", "kisisel-gelisim", "115.00", "good",
     "İkna üzerine temel kitap. Az altı çizili."),
    ("Sessiz: İçedönüklerin Gücü", "Susan Cain", "9780307352156", "kisisel-gelisim", "105.00", "good",
     "İçedönüklük üzerine. İyi durumda."),
    ("Şimdinin Gücü", "Eckhart Tolle", "9781577314806", "kisisel-gelisim", "95.00", "new",
     "Farkındalık üzerine. Çok temiz."),
    ("Azim (Grit)", "Angela Duckworth", "9781501111112", "kisisel-gelisim", "110.00", "good",
     "Tutku ve sebat üzerine. Az notlu."),
]


# Demo kullanıcılar — her birine birkaç ilan dağıtılacak
DEMO_USERS = [
    ("demo_ali",    "Ali Yılmaz",    "ali@demo.local"),
    ("demo_ayse",   "Ayşe Demir",    "ayse@demo.local"),
    ("demo_can",    "Can Öztürk",    "can@demo.local"),
    ("demo_defne",  "Defne Aydın",   "defne@demo.local"),
    ("demo_emre",   "Emre Kaya",     "emre@demo.local"),
    ("demo_zeynep", "Zeynep Acar",   "zeynep@demo.local"),
]

DEMO_PASSWORD = "demo1234"


def _fetch(url, timeout=8):
    """URL'i indir, hata olursa None döner."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "BookMarket Seeder/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def _download_cover(isbn):
    """ISBN ile birden çok kaynaktan kapak çek. Bulunamazsa None döner."""
    if not isbn:
        return None

    # 1) Open Library Covers — önce büyük (L), sonra orta (M) boyut.
    #    `default=false` boş kapakta 404 verir; yine de küçük dosyaları eleriz.
    for size in ("L", "M"):
        url = f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg?default=false"
        data = _fetch(url)
        if data and len(data) >= 500:
            return data

    # 2) Google Books — ISBN ile arayıp thumbnail görselini çek.
    payload = _fetch(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}")
    if payload:
        try:
            items = json.loads(payload).get("items") or []
            if items:
                links = items[0].get("volumeInfo", {}).get("imageLinks", {})
                thumb = links.get("thumbnail") or links.get("smallThumbnail")
                if thumb:
                    img = _fetch(thumb.replace("http://", "https://"))
                    if img and len(img) >= 500:
                        return img
        except Exception:
            pass

    return None


# Üretilen placeholder kapaklar için arka plan paleti.
PLACEHOLDER_COLORS = [
    (38, 70, 83), (42, 157, 143), (138, 177, 125), (231, 111, 81),
    (244, 162, 97), (61, 90, 128), (90, 61, 128), (128, 61, 90),
]


# Depoya gömülü DejaVu fontu — Türkçe karakterleri (ğ, ş, İ, ı...) her
# ortamda (macOS/Linux) doğru çizer; sistem fontuna güvenmeyiz.
# rich_seed.py -> books/management/commands/ ; fontlar books/fonts/ altında.
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "fonts")


def _load_font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)  # Pillow 10.1+
        except TypeError:
            return ImageFont.load_default()


def _placeholder_cover(title, author):
    """Kapağı bulunamayan kitaplar için başlık+yazar yazan görsel üret."""
    w, h = 400, 600
    bg = PLACEHOLDER_COLORS[sum(map(ord, title)) % len(PLACEHOLDER_COLORS)]
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w, 90], fill=tuple(max(0, c - 25) for c in bg))

    title_font = _load_font(34, bold=True)
    author_font = _load_font(22)

    y = 170
    for line in textwrap.wrap(title, width=16)[:5]:
        tw = draw.textlength(line, font=title_font)
        draw.text(((w - tw) / 2, y), line, font=title_font, fill=(255, 255, 255))
        y += 46

    aw = draw.textlength(author, font=author_font)
    draw.text(((w - aw) / 2, y + 20), author, font=author_font, fill=(235, 235, 235))

    label = "Kapak görseli yok"
    lw = draw.textlength(label, font=author_font)
    draw.text(((w - lw) / 2, h - 60), label, font=author_font, fill=(255, 255, 255))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Gerçekçi 120+ kitap, 6 kullanıcı, kategori ve örnek mesajlaşma ile dolu demo verisi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep", action="store_true",
            help="Mevcut demo veriyi silme; üzerine ekle.",
        )
        parser.add_argument(
            "--no-covers", action="store_true",
            help="Open Library'den kapak indirme (offline mod).",
        )

    def handle(self, *args, **options):
        keep = options["keep"]
        skip_covers = options["no_covers"]

        if not keep:
            self.stdout.write("Eski demo veriler temizleniyor...")
            User.objects.filter(username__in=[u[0] for u in DEMO_USERS]).delete()

        # Kategoriler
        cat_map = {}
        for name, slug in CATEGORIES:
            obj, _ = Category.objects.get_or_create(
                slug=slug, defaults={"name": name},
            )
            obj.name = name
            obj.save()
            cat_map[slug] = obj
        self.stdout.write(self.style.SUCCESS(f"{len(CATEGORIES)} kategori hazır."))

        # Kullanıcılar
        users = []
        for username, full_name, email in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": full_name.split()[0],
                          "last_name": " ".join(full_name.split()[1:])},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users.append(user)
        self.stdout.write(self.style.SUCCESS(
            f"{len(users)} demo kullanıcı (şifre: {DEMO_PASSWORD})."
        ))

        # Kitaplar
        random.seed(42)
        cover_hits = 0
        cover_misses = 0
        created_books = []
        with transaction.atomic():
            for i, (title, author, isbn, cat_slug, price, condition, desc) in enumerate(BOOKS):
                seller = users[i % len(users)]
                if Book.objects.filter(title=title, seller=seller).exists():
                    continue
                book = Book(
                    seller=seller,
                    category=cat_map.get(cat_slug),
                    title=title,
                    author=author,
                    description=desc,
                    price=Decimal(price),
                    condition=condition,
                )
                if not skip_covers:
                    cover = _download_cover(isbn)
                else:
                    cover = None
                if cover:
                    cover_hits += 1
                    book.image.save(f"{isbn or i}.jpg", ContentFile(cover), save=False)
                else:
                    cover_misses += 1
                    book.image.save(
                        f"placeholder_{i}.png",
                        ContentFile(_placeholder_cover(title, author)),
                        save=False,
                    )
                book.save()
                created_books.append(book)

        self.stdout.write(self.style.SUCCESS(
            f"{len(created_books)} kitap eklendi (kapak: {cover_hits} bulundu, {cover_misses} placeholder)."
        ))

        if not created_books:
            self.stdout.write(self.style.WARNING(
                "Yeni kitap eklenmedi (zaten mevcuttu). Mesajlaşma/favori sahnesi atlanıyor."
            ))
            return

        # Senaryo: bazı kitaplar satılsın
        for book in random.sample(created_books, k=min(15, len(created_books))):
            buyer = random.choice([u for u in users if u.id != book.seller_id])
            with transaction.atomic():
                locked = Book.objects.select_for_update().get(pk=book.pk)
                if locked.is_sold or Order.objects.filter(book=locked).exists():
                    continue
                Order.objects.create(
                    buyer=buyer, book=locked,
                    address=f"Demo adres — {buyer.first_name}",
                )
                locked.is_sold = True
                locked.save(update_fields=["is_sold"])
        self.stdout.write(self.style.SUCCESS("Birkaç kitap satılmış olarak işaretlendi."))

        # Favoriler
        for book in random.sample(created_books, k=min(35, len(created_books))):
            fans = random.sample(users, k=random.randint(1, 3))
            for u in fans:
                if u.id != book.seller_id:
                    book.favorited_by.add(u)
        self.stdout.write(self.style.SUCCESS("Rastgele favoriler eklendi."))

        # Mesajlaşma örneği
        for book in random.sample(
            [b for b in created_books if not b.is_sold],
            k=min(10, len([b for b in created_books if not b.is_sold])),
        ):
            buyer = random.choice([u for u in users if u.id != book.seller_id])
            Message.objects.create(
                sender=buyer, receiver=book.seller, book=book,
                body=f"Merhaba, {book.title} hâlâ satışta mı? Pazarlık şansı var mı?",
            )
            Message.objects.create(
                sender=book.seller, receiver=buyer, book=book,
                body="Merhaba, evet hâlâ satışta. Fiyatta küçük indirim yapabilirim.",
            )
        self.stdout.write(self.style.SUCCESS("Örnek mesajlaşmalar eklendi."))

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Tarayıcıda dene:"))
        self.stdout.write(f"  Giriş: /users/login/  → demo_ali / {DEMO_PASSWORD}")
        self.stdout.write("  Admin: /admin/")
        self.stdout.write("  API:   /api/books/")
