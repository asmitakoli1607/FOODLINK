import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask,g,session,request,redirect,url_for,render_template,flash
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
app=Flask(__name__);app.secret_key='foodlink';DB='foodlink.db'
def db():
 if 'db' not in g:g.db=sqlite3.connect(DB);g.db.row_factory=sqlite3.Row
 return g.db
@app.teardown_appcontext
def close(e=None):
 if 'db' in g:g.db.close()
def init():
 c=db();c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT);CREATE TABLE IF NOT EXISTS food_posts(id INTEGER PRIMARY KEY,provider_id INTEGER,title TEXT,quantity INTEGER,location TEXT,pickup_by TEXT,notes TEXT,status TEXT DEFAULT 'available',claimed_by INTEGER,created_at TEXT);CREATE TABLE IF NOT EXISTS produce_listings(id INTEGER PRIMARY KEY,farmer_id INTEGER,vegetable TEXT,quantity REAL,unit TEXT,price REAL,location TEXT,contact_note TEXT,status TEXT DEFAULT 'available',buyer_id INTEGER,created_at TEXT);""")
 if not c.execute('select count(*) n from users').fetchone()['n']:
  c.executemany('insert into users(name,email,password,role) values(?,?,?,?)',[('Green Bowl Hotel','provider@foodlink.demo','demo123','provider'),('Care Hands NGO','ngo@foodlink.demo','demo123','ngo'),('Sunrise Organic Farm','farmer@foodlink.demo','demo123','farmer'),('FoodLink Admin','admin@foodlink.demo','demo123','admin')]);c.execute("insert into food_posts(provider_id,title,quantity,location,pickup_by,notes,status,created_at) values(1,'Fresh vegetarian meal boxes',30,'College Road Canteen','Today, 8:00 PM','Packed within last hour','available',?)",(datetime.now().strftime('%d %b, %I:%M %p'),));c.execute("insert into produce_listings(farmer_id,vegetable,quantity,unit,price,location,contact_note,status,created_at) values(3,'Organic tomatoes',80,'kg',32,'Nashik Farm Belt','Call farmer after sending request','available',?)",(datetime.now().strftime('%d %b, %I:%M %p'),));c.commit()
def auth(roles=None):
 def d(f):
  @wraps(f)
  def w(*a,**k):
   if not session.get('user_id'):flash('Please log in first.','warning');return redirect('/login')
   if roles and session['role'] not in roles:flash('This option is not available for your role.','danger');return redirect('/dashboard')
   return f(*a,**k)
  return w
 return d
@app.route('/')
def home():
 s=db().execute("select count(*) posts,coalesce(sum(case when status='picked_up' then quantity end),0) rescued from food_posts").fetchone();m=db().execute("select count(*) n from produce_listings where status='available'").fetchone()['n'];return render_template('home.html',s=s,m=m)
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=db().execute('select * from users where email=? and password=?',(request.form['email'],request.form['password'])).fetchone()
  if u:session.update(user_id=u['id'],name=u['name'],role=u['role']);return redirect('/dashboard')
  flash('Invalid email or password.','danger')
 return render_template('login.html')
@app.route('/logout')
def logout():session.clear();return redirect('/')
@app.route('/dashboard')
@auth()
def dashboard():
 q='select p.*,a.name provider,b.name claimant from food_posts p join users a on p.provider_id=a.id left join users b on p.claimed_by=b.id';role=session['role']
 if role=='provider':q+=' where p.provider_id='+str(session['user_id'])
 elif role=='ngo':q+=" where p.status in ('available','claimed')"
 posts=db().execute(q+' order by p.id desc').fetchall();s=db().execute("select count(*) total,coalesce(sum(case when status='picked_up' then quantity end),0) rescued,coalesce(sum(case when status='compost' then quantity end),0) composted from food_posts").fetchone();return render_template('dashboard.html',posts=posts,s=s)
@app.route('/post',methods=['GET','POST'])
@auth(['provider'])
def post():
 if request.method=='POST':
  f=request.form;db().execute('insert into food_posts(provider_id,title,quantity,location,pickup_by,notes,created_at) values(?,?,?,?,?,?,?)',(session['user_id'],f['title'],f['quantity'],f['location'],f['pickup_by'],f['notes'],datetime.now().strftime('%d %b, %I:%M %p')));db().commit();flash('Food alert published.','success');return redirect('/dashboard')
 return render_template('post.html')
@app.post('/claim/<int:i>')
@auth(['ngo'])
def claim(i):db().execute("update food_posts set status='claimed',claimed_by=? where id=? and status='available'",(session['user_id'],i));db().commit();flash('Food claimed successfully.','success');return redirect('/dashboard')
@app.post('/pickup/<int:i>')
@auth(['ngo','admin'])
def pickup(i):db().execute("update food_posts set status='picked_up' where id=?",(i,));db().commit();flash('Pickup completed.','success');return redirect('/dashboard')
@app.post('/compost/<int:i>')
@auth(['provider','admin'])
def compost(i):db().execute("update food_posts set status='compost' where id=?",(i,));db().commit();flash('Redirected to compost partner.','success');return redirect('/dashboard')
@app.route('/market')
def market():
 q='select p.*,u.name farmer,b.name buyer from produce_listings p join users u on p.farmer_id=u.id left join users b on p.buyer_id=b.id order by p.id desc';return render_template('market.html',items=db().execute(q).fetchall())
@app.route('/market/add',methods=['GET','POST'])
@auth(['farmer'])
def add_produce():
 if request.method=='POST':
  f=request.form;db().execute('insert into produce_listings(farmer_id,vegetable,quantity,unit,price,location,contact_note,created_at) values(?,?,?,?,?,?,?,?)',(session['user_id'],f['vegetable'],f['quantity'],f['unit'],f['price'],f['location'],f['contact_note'],datetime.now().strftime('%d %b, %I:%M %p')));db().commit();flash('Fresh-produce listing is live.','success');return redirect('/market')
 return render_template('add_produce.html')
@app.post('/market/request/<int:i>')
@auth(['provider'])
def request_produce(i):
 x=db().execute("update produce_listings set status='requested',buyer_id=? where id=? and status='available'",(session['user_id'],i));db().commit();flash('Request sent directly to the farmer.' if x.rowcount else 'This produce is no longer available.','success' if x.rowcount else 'warning');return redirect('/market')
@app.route('/predict',methods=['GET','POST'])
@auth(['provider','admin'])
def predict():
 r=None;h=[34,37,40,35,43,49,53]
 if request.method=='POST':
  rows=[]
  for sales in range(25,81,5):
   for week in (0,1):
    for fest in (0,1):rows.append([week,sales,fest,round(sales*.75+week*7+fest*12)])
  d=pd.DataFrame(rows,columns=['week','sales','fest','meals']);m=RandomForestRegressor(n_estimators=120,random_state=42).fit(d[['week','sales','fest']],d.meals);f=request.form;r=round(m.predict([[int(f['day']=='weekend'),float(f['sales']),int('festival' in f)]])[0])
 return render_template('predict.html',r=r,h=h)
with app.app_context():init()
if __name__=='__main__':app.run(debug=True)
