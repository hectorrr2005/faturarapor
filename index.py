from flask import Flask, render_template, request
import pyodbc
from datetime import datetime
from wtforms import Form, DateField

# Günün Tarihini alalım
bugun = datetime.now().strftime('%Y%m%d')

# Form tarih sınıfı
class DateForm(Form):
    tarih = DateField('datepicker', format='%y%m%d', default=datetime.now())

# Evrak bazlı siparişleri çekelim
def sipariscek(tarih = bugun):
    cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=KAYAPLASSV;DATABASE=MikroDB_V15_KAYAPLAS;UID=app;PWD=kayalar2018')
    cursor = cnxn.cursor()
    cursor.execute("Select * from SIPARISLER_CHOOSE_40_ULAS WHERE msg_S_0240 = ?", (tarih))
    result = cursor.fetchall()
    return result

# Satış faturalarını çekelim
def vericek(tarih = bugun):
    cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=KAYAPLASSV;DATABASE=MikroDB_V15_KAYAPLAS;UID=app;PWD=kayalar2018')
    cursor = cnxn.cursor()
    cursor.execute("Select * from dbo.fn_SatisFaturalariAnalizKupuOzel(?,?,N'')", (tarih, tarih))
    result = cursor.fetchall()
    return result

# Satış faturaları detaylarını çekelim
def detaycek(id):
    cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=KAYAPLASSV;DATABASE=MikroDB_V15_KAYAPLAS;UID=app;PWD=kayalar2018')
    cursor = cnxn.cursor()
    cursor.execute("Select * from fn_SatisFaturalariDetayi(?)", (id))
    result = cursor.fetchall()
    return result

# Fatura hizmet faturasıysa detaylarını buradan çekiyoruz
def hizmetdetaycek(seri,sira):
    cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=KAYAPLASSV;DATABASE=MikroDB_V15_KAYAPLAS;UID=app;PWD=kayalar2018')
    cursor = cnxn.cursor()
    cursor.execute("""SELECT cha_kasa_hizkod ,dbo.fn_HizmetIsmi(cha_kasa_hizkod) as [hizmet_ismi] ,
                    [cha_miktari],[cha_aratoplam]/[cha_miktari] as [birim_fiyat] ,[cha_aratoplam] ,
                    CASE WHEN cha_vergipntr=1 THEN cha_vergi1 WHEN cha_vergipntr=2 THEN cha_vergi2 
                    WHEN cha_vergipntr=3 THEN cha_vergi3 WHEN cha_vergipntr=4 THEN cha_vergi4 END AS [vergi]  ,
                    dbo.fn_CarininIsminiBul(0,cha_kod) as [cari] ,cha_ft_iskonto1  ,cha_ft_iskonto2 
                    FROM [dbo].[CARI_HESAP_HAREKETLERI] where cha_cinsi = 8 and [cha_evrakno_seri] = ? 
                    and [cha_evrakno_sira] = ?""", (seri,sira))
    result = cursor.fetchall()
    return result

# Siparişlerin detaylarını çekiyoruz
def siparisdetaycek(seri,sira):
    cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=KAYAPLASSV;DATABASE=MikroDB_V15_KAYAPLAS;UID=app;PWD=kayalar2018')
    cursor = cnxn.cursor()
    cursor.execute("""SELECT sip_evrakno_seri, sip_evrakno_sira, dbo.fn_CarininIsminiBul(0,sip_musteri_kod), 
                    dbo.fn_StokIsmi(sip_stok_kod), sip_b_fiyat, sip_miktar, sip_teslim_miktar, sip_tutar, sip_vergi,
                    sip_iskonto_1, sip_iskonto_2, sip_opno, sip_aciklama, sip_aciklama2, dbo.fn_KullaniciUzunAdi(sip_OnaylayanKulNo) 
                    FROM [dbo].[SIPARISLER] where [sip_evrakno_seri] = ? and [sip_evrakno_sira] = ?""", (seri,sira))
    result = cursor.fetchall()
    return result

# Fatura evrak no çekiyoruz. Hizmet faturası mı kontrol için cari hareket cinsini de çekiyoruz.
def faturakontrol(id):
    cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=KAYAPLASSV;DATABASE=MikroDB_V15_KAYAPLAS;UID=app;PWD=kayalar2018')
    cursor = cnxn.cursor()
    cursor.execute("Select cha_cinsi, cha_evrakno_seri, cha_evrakno_sira from CARI_HESAP_HAREKETLERI WHERE cha_RECid_RECno = ?", (id))
    result = cursor.fetchall()
    return result

# Sipariş evrak numaralarını çekiyoruz.
def sipariskontrol(id):
    cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=KAYAPLASSV;DATABASE=MikroDB_V15_KAYAPLAS;UID=app;PWD=kayalar2018')
    cursor = cnxn.cursor()
    cursor.execute("Select sip_evrakno_seri, sip_evrakno_sira from SIPARISLER WHERE sip_RECid_RECno = ?", (id))
    result = cursor.fetchall()
    return result

# Fatura ve sipariş evrak aratoplamlarını hesaplıyoruz.
def aratoplam(veri,i,j,k):
    toplam = 0
    for row in veri:
        toplam = toplam + (row[i]-(row[j]+row[k]))
    return toplam

# Fatura ve sipariş evrak toplam vergisi
def toplamvergi(veri,i):
    toplam = 0
    for row in veri:
        toplam = toplam + row[i]
    return toplam

# Fatura ve siparişlerin günlük toplamları
def toplamhesapla(veri,i):
    toplam = 0
    for row in veri:
        toplam = toplam + row[i]
    return toplam


app = Flask(__name__)

# Fatura listesi görünümü
@app.route("/", methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        tarih = request.form['date']
        result = vericek(tarih)
        toplam = toplamhesapla(result,14)
        return render_template("index.html", result=result, toplam=toplam)
    else:
        result = vericek()
        toplam = toplamhesapla(result,14)
        return render_template("index.html", result=result, toplam=toplam)

# Fatura detayı görünümü
@app.route("/detay/<string:id>/")
def detay(id):
    hareketcinsi = faturakontrol(id)
    detaylar = detaycek(id)
    aratop = aratoplam(detaylar,4,7,8)
    topvergi = toplamvergi(detaylar,5)
    if hareketcinsi[0][0] == 8:
        seri = hareketcinsi[0][1]
        sira = hareketcinsi[0][2]
        detayhizmet = hizmetdetaycek(seri,sira)
        aratop = aratoplam(detayhizmet,4,7,8)
        topvergi = toplamvergi(detayhizmet,5)
        return render_template("detayhizmet.html", id=id, detayhizmet=detayhizmet, aratop=aratop, topvergi=topvergi)
    else:
        return render_template("detay.html", id=id, detaylar=detaylar, aratop=aratop, topvergi=topvergi)

# Sipariş listesi görünümü
@app.route("/siparisler", methods=['POST', 'GET'])
def siparisler():
    if request.method == 'POST':
        tarih = request.form['date']
        result = sipariscek(tarih)
        toplam = toplamhesapla(result, 11)
        return render_template("siparisler.html", result=result, toplam=toplam)
    else:
        result = sipariscek()
        toplam = toplamhesapla(result, 11)
        return render_template("siparisler.html", result=result, toplam=toplam)

# Sipariş detayı görünümü
@app.route("/siparisdetay/<string:id>/")
def sipdetay(id):
    sipserisira = sipariskontrol(id)
    seri = sipserisira[0][0]
    sira = sipserisira[0][1]
    detaylar = siparisdetaycek(seri,sira)
    aratop = aratoplam(detaylar,7,9,10)
    topvergi = toplamvergi(detaylar,8)
    return render_template("siparisdetay.html", id=id, detaylar=detaylar, aratop=aratop, topvergi=topvergi)

# Sipariş teslimat detayı görünümü
@app.route("/siparisteslimdetay/<string:id>/")
def siptesdetay(id):
    sipserisira = sipariskontrol(id)
    seri = sipserisira[0][0]
    sira = sipserisira[0][1]
    detaylar = siparisdetaycek(seri,sira)
    return render_template("siparisteslimdetay.html", id=id, detaylar=detaylar)

if __name__ == "__main__":
    app.secret_key = 'secret1234'
    app.run(debug=True)