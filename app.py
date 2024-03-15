from flask import Flask, render_template, url_for, redirect, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
from datetime import timedelta
from flask_migrate import Migrate
import re


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'SANSÜR' #Burayı sen değiştirip saklayacaksın önemli!
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


ADMIN_USERNAMES = {'admin','yozgat.m66','bay.beyaz'}  


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
                          

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=True) 
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    
    kaydedildi = db.relationship(
        'YaziKaydet',
        foreign_keys='YaziKaydet.user_id',
        backref='user',lazy='dynamic'
    )

    def kaydet(self,yazi):
        if not self.kaydetti_mi(yazi):
            kaydet = YaziKaydet(user_id=self.id, yazi_id=yazi.id)
            db.session.add(kaydet)
            db.session.commit()
        else:
            YaziKaydet.query.filter_by(
                user_id=self.id,
                yazi_id=yazi.id).delete()
            db.session.commit()
            


    def kaydetti_mi(self,yazi):
        #print(YaziKaydet.query.all()[0].user_id,YaziKaydet.query.all()[0].yazi_id, self.id, yazi.id)
        return YaziKaydet.query.filter(
            YaziKaydet.user_id == self.id,
            YaziKaydet.yazi_id == yazi.id).count() > 0


class Yazilar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(10000), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    baslik = db.Column(db.String(50), nullable=False, unique=True)
    kaydedilme_sayısı = db.relationship('YaziKaydet',backref='Yazilar',lazy='dynamic')
    kategori = db.Column(db.String(50),nullable=False, default="Diğer")


class YaziKaydet(db.Model):
    __tablename__ = 'yazi_kaydet'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    yazi_id = db.Column(db.Integer, db.ForeignKey('yazilar.id'))

@app.before_request
def make_session_permanent():
    session.permanent = True 



@app.route('/', methods=['GET', 'POST'])
def home():
    if current_user.is_authenticated:
        filter = request.args.get('filter',  type = str)
        arama = False
        arama_bulunan = 0
        aranan = " "
        if request.method == 'POST':
            yazilar = Yazilar.query.filter(Yazilar.baslik.contains(request.form.get('arama'))).all()
            if not yazilar:
                yazilar = Yazilar.query.filter(Yazilar.message.contains(request.form.get('arama'))).all()
            arama = True
            if yazilar:
                arama_bulunan = len(yazilar)
            print('arama bulunan => ' + str(arama_bulunan))
            aranan = request.form.get('arama')
        else:

            if filter:
                yazilar = Yazilar.query.filter(Yazilar.kategori == filter)
                
                if  yazilar.count() < 1:
                    yazilar = None
            else:
                yazilar = Yazilar.query.all()
        return  render_template('home.html', yazilar = yazilar, c_user = current_user, filtre=filter,kategoriler = ["diğer", "siyaset", "spor", "kişisel-gelişim", "teknoloji"], arama=arama, arama_bulunan=arama_bulunan, aranan=aranan)
    else:
        return "Lütfen giriş yapın"



@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        password = request.form.get('password')
        username = request.form.get('username')
        user = User.query.filter_by(username=username.lower()).first()
        if user:
            if bcrypt.check_password_hash(user.password, password):
                login_user(user)
                #user.last_login_device = request.user_agent.string
                #user.last_login_ip = request.remote_addr
                db.session.commit()

                return redirect(url_for('home'))
            else:
                flash("Kullanıcı adı veya şifre hatalı.")
                
    return render_template('login.html')


@ app.route('/register', methods=['GET', 'POST'])
def register():
    

    if request.method == 'POST':
        password = request.form.get('password')
        username = request.form.get('username')
        email = request.form.get('email')

        hashed_password = bcrypt.generate_password_hash(password)
        new_user = User(username=username.lower(), password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
        

    return render_template('register.html')



@app.route('/yaziyaz' , methods=['GET', 'POST'])
@login_required
def yazi_yaz():

    if request.method == 'POST':
        if current_user.is_authenticated:
            user_info = User.query.get(current_user.id)


            data = request.form.get('yazi')
            kategori = request.form.get('kategori')
            baslik = request.form.get('baslik')

            baslik = baslik.rstrip()
            baslik = baslik.lstrip()

            data = data.lstrip()
            data = data.rstrip()

            data = data.partition('>')[0] + data.partition('>')[-1].lstrip()

            if Yazilar.query.filter_by(baslik=baslik).first():
                flash('Zaten böyle bir başlık var lütfen farklı bir başlık seçin!')
                return render_template('yazi_yaz.html')


            if not baslik or not data:
                flash('Başlık ya da Metin boş olamaz!')
                return render_template('yazi_yaz.html')


            if len(data) < 50 :
                flash('Yazının uzunluğu 50 karakterden az olamaz!')
                return render_template('yazi_yaz.html')

            yeni_yazi = Yazilar(message=data, user_id=current_user.id, baslik = baslik, kategori=kategori)   
            db.session.add(yeni_yazi)
            db.session.commit()
            

    return render_template('yazi_yaz.html')

@app.route('/yazi/<yazi_baslik>')
def yazi(yazi_baslik):

    yazi = Yazilar.query.filter_by(baslik=yazi_baslik).first()
    
    yazar = User.query.filter_by(id=yazi.user_id).first()
    print("'"+Yazilar.query.all()[0].baslik+"'" +"'"+yazi_baslik+"'")
    if yazi:
        return render_template('yazi.html', yazi =yazi,user=current_user, yazar = yazar.username)
    return redirect(url_for('home'))

#sorun url'den geçerken son boşluğu siliyor bu yüzden bir tanesinde boşluk olmuyor database de bulamıyor

@app.route('/yazi/<yazi_baslik>/kaydet')
@login_required
def kaydet(yazi_baslik):
    yazi = Yazilar.query.filter_by(baslik=yazi_baslik).first()
    if yazi:
        current_user.kaydet(yazi)
        return redirect(f'/yazi/{yazi_baslik}')
    return redirect(f'/yazi/{yazi_baslik}')

@app.route('/kaydedilenler')
@login_required
def kaydedilenler():
    kaydedilenler = current_user.kaydedildi.all()
    yazilar = []
    for kaydedilen in kaydedilenler:
        yazilar.append(Yazilar.query.filter_by(id=kaydedilen.yazi_id).first())
        print(kaydedilen.yazi_id)
    
    return render_template('kaydedilenler.html', yazilar=yazilar)

@app.route('/yazi/<yazi_baslik>/kaldir')
@login_required
def kaldir(yazi_baslik):
    yazi = Yazilar.query.filter(Yazilar.baslik == yazi_baslik)[0]
    if current_user.id == yazi.user_id:
        Yazilar.query.filter_by(baslik=yazi_baslik).delete()
        db.session.commit()
    return redirect('/')

@app.route('/yazi/<yazi_id>/kaldir_id')
@login_required
def kaldir_id(yazi_id):
    yazi = Yazilar.query.filter_by(id=yazi_id).delete()
    db.session.commit()
    return redirect('/')
"""
@app.route('/ara', methods=['GET', 'POST'] )
def ara():
    if request.method == 'POST':
        yazilar = Yazilar.query.filter(Yazilar.baslik.contains(request.form.get('arama'))).all()
        if not yazilar:
            yazilar = Yazilar.query.filter(Yazilar.message.contains(request.form.get('arama'))).all()
        return render_template('home.html', yazilar = yazilar, c_user = current_user, kategoriler = ["diğer", "siyaset", "spor", "kişisel-gelişim", "teknoloji"])
    return redirect('/')
"""
if __name__ == "__main__":
    #from waitress import serve
    #serve(app, host="87.248.157.245", port=8080)
    app.run(host="0.0.0.0", debug=True)

