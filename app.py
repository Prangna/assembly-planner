from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'assembly-planner-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///assembly.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# ── Models ──────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(200))
    plans = db.relationship('AssemblyPlan', backref='user', lazy=True)

class AssemblyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(20))
    theme = db.Column(db.String(200))
    class_name = db.Column(db.String(50))
    venue = db.Column(db.String(100))
    start_time = db.Column(db.String(10))
    slots = db.Column(db.Text, default='[]')
    students = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── Base HTML ────────────────────────────────────────────────────────────────

def base_html(content, title="Assembly Planner"):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Rathore's Assembly Planner</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#0e0e11;--surface:#17171b;--surface2:#1f1f25;--border:rgba(255,255,255,0.08);--border2:rgba(255,255,255,0.14);--text:#f0eff4;--muted:#8a8996;--accent:#a78bfa;--accent2:#7c3aed;--green:#34d399;--red:#f87171;--yellow:#fbbf24}}
body{{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;font-size:15px;min-height:100vh;line-height:1.6}}
header{{padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border)}}
.logo{{font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;display:flex;align-items:center;gap:8px}}
.logo-dot{{width:10px;height:10px;border-radius:50%;background:var(--accent)}}
nav a{{color:var(--muted);text-decoration:none;font-size:13px;margin-left:16px}}
nav a:hover{{color:var(--text)}}
main{{max-width:900px;margin:0 auto;padding:2rem 1.5rem 4rem}}
.card{{background:var(--surface);border:1px solid var(--border2);border-radius:16px;padding:1.5rem;margin-bottom:1rem}}
.card h2{{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:600;margin-bottom:1rem}}
input,select,textarea{{width:100%;background:var(--surface2);border:1px solid var(--border2);border-radius:8px;padding:8px 12px;color:var(--text);font-size:13px;font-family:'DM Sans',sans-serif;outline:none;margin-bottom:10px}}
input:focus,select:focus,textarea:focus{{border-color:var(--accent)}}
label{{font-size:12px;color:var(--muted);display:block;margin-bottom:4px}}
.btn{{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;border-radius:10px;font-size:13px;font-weight:500;cursor:pointer;border:none;font-family:'DM Sans',sans-serif;transition:opacity 0.15s}}
.btn:hover{{opacity:0.85}}
.btn-primary{{background:linear-gradient(135deg,#7c3aed,#a78bfa);color:#fff}}
.btn-outline{{background:transparent;color:var(--text);border:1px solid var(--border2)}}
.btn-danger{{background:rgba(248,113,113,0.15);color:var(--red);border:1px solid rgba(248,113,113,0.3)}}
.btn-green{{background:rgba(52,211,153,0.15);color:var(--green);border:1px solid rgba(52,211,153,0.3)}}
.btn-sm{{padding:6px 12px;font-size:12px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.grid-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}
@media(max-width:600px){{.grid-2,.grid-3{{grid-template-columns:1fr}}}}
.tag{{font-size:11px;padding:2px 8px;border-radius:999px;background:var(--surface2);border:1px solid var(--border);color:var(--muted);display:inline-block}}
.tag.green{{background:rgba(52,211,153,0.1);border-color:rgba(52,211,153,0.3);color:var(--green)}}
.tag.purple{{background:rgba(167,139,250,0.1);border-color:rgba(167,139,250,0.3);color:var(--accent)}}
.alert{{padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:1rem}}
.alert-error{{background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);color:var(--red)}}
.alert-success{{background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.3);color:var(--green)}}
.slot-item{{display:flex;align-items:center;gap:8px;background:var(--surface2);border-radius:8px;padding:8px 12px;margin-bottom:6px;cursor:grab}}
.slot-item:active{{cursor:grabbing}}
.drag-handle{{color:var(--muted);font-size:14px;flex-shrink:0;user-select:none}}
.slot-num{{width:24px;height:24px;border-radius:50%;background:var(--surface);border:1px solid var(--border2);display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--muted);flex-shrink:0}}
.slot-dur-input{{width:60px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:3px 6px;color:var(--text);font-size:12px;text-align:center;margin:0}}
.ai-output{{background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:1rem;font-size:13px;line-height:1.8;white-space:pre-wrap;margin-top:8px;display:none}}
.ai-output.visible{{display:block}}
.plan-card{{background:var(--surface);border:1px solid var(--border2);border-radius:12px;padding:1rem 1.25rem;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}}
.print-area{{display:none}}
@media print{{body{{background:#fff;color:#000}}.print-area{{display:block}}.no-print{{display:none}}}}
footer{{text-align:center;padding:1.5rem;border-top:1px solid var(--border);color:var(--muted);font-size:12px}}
.section-row{{display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap}}
.slot-template-btn{{font-size:12px;padding:5px 10px;border-radius:8px;background:var(--surface2);border:1px solid var(--border2);color:var(--muted);cursor:pointer;margin-right:6px;margin-bottom:6px}}
.slot-template-btn:hover{{border-color:var(--accent);color:var(--accent)}}
</style>
</head>
<body>
<header class="no-print">
  <div class="logo"><span class="logo-dot"></span> Assembly Planner</div>
  <nav>
    {'<a href="/dashboard">Dashboard</a><a href="/new-plan">New Plan</a><a href="/logout">Logout</a>' if current_user.is_authenticated else '<a href="/login">Login</a><a href="/register">Register</a>'}
    <a href="https://forms.gle/MeaBkvtQ1r6FDQPbA" target="_blank" style="background:linear-gradient(135deg,#7c3aed,#a78bfa);color:#fff;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:500;text-decoration:none">💬 Give Feedback</a>
  </nav>
</header>
{content}
<footer class="no-print">Built by Poonam Rathore &nbsp;·&nbsp; <a href="https://rathoresacademy.wordpress.com" style="color:var(--accent);text-decoration:none">rathoresacademy.wordpress.com</a></footer>
</body>
</html>'''

# ── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    content = '''
<main>
  <div style="text-align:center;padding:4rem 1rem">
    <div style="font-family:Syne,sans-serif;font-size:clamp(2rem,5vw,3rem);font-weight:700;letter-spacing:-0.03em;margin-bottom:1rem">
      AI-Powered<br><span style="color:var(--accent)">Assembly Planner</span>
    </div>
    <p style="color:var(--muted);max-width:480px;margin:0 auto 2rem">Plan your school morning assembly, assign student roles, and generate AI-powered speeches, quizzes and scripts in minutes.</p>
    <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
      <a href="/register" class="btn btn-primary">Get started free</a>
      <a href="/login" class="btn btn-outline">Login</a>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:3rem;max-width:700px;margin-left:auto;margin-right:auto">
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1rem;text-align:center"><div style="font-size:24px;margin-bottom:6px">📅</div><div style="font-size:13px;font-weight:500">Schedule Builder</div><div style="font-size:12px;color:var(--muted)">Drag & reorder slots</div></div>
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1rem;text-align:center"><div style="font-size:24px;margin-bottom:6px">👨‍🎓</div><div style="font-size:13px;font-weight:500">Student Roles</div><div style="font-size:12px;color:var(--muted)">Assign and track</div></div>
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1rem;text-align:center"><div style="font-size:24px;margin-bottom:6px">🤖</div><div style="font-size:13px;font-weight:500">AI Content</div><div style="font-size:12px;color:var(--muted)">Speeches, scripts, quiz</div></div>
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1rem;text-align:center"><div style="font-size:24px;margin-bottom:6px">🖨️</div><div style="font-size:13px;font-weight:500">Run Sheet</div><div style="font-size:12px;color:var(--muted)">Print ready</div></div>
    </div>
  </div>
</main>'''
    return base_html(content, "Home")

@app.route('/register', methods=['GET','POST'])
def register():
    error = ''
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        school = request.form.get('school','').strip()
        password = request.form.get('password','')
        if User.query.filter_by(email=email).first():
            error = 'Email already registered. Please login.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        else:
            user = User(name=name, email=email, school=school, password=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('dashboard'))
    content = f'''
<main style="max-width:440px">
  <div class="card" style="margin-top:2rem">
    <h2>Create your account</h2>
    {f'<div class="alert alert-error">{error}</div>' if error else ''}
    <form method="POST">
      <label>Your name</label><input name="name" placeholder="Poonam Rathore" required />
      <label>Email</label><input name="email" type="email" placeholder="your@email.com" required />
      <label>School name</label><input name="school" placeholder="Govt. Girls School, Delhi" />
      <label>Password</label><input name="password" type="password" placeholder="Min 6 characters" required />
      <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;margin-top:4px">Create account</button>
    </form>
    <p style="font-size:13px;color:var(--muted);margin-top:12px;text-align:center">Already have an account? <a href="/login" style="color:var(--accent)">Login</a></p>
  </div>
</main>'''
    return base_html(content, "Register")

@app.route('/login', methods=['GET','POST'])
def login_page():
    error = ''
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        error = 'Incorrect email or password.'
    content = f'''
<main style="max-width:440px">
  <div class="card" style="margin-top:2rem">
    <h2>Login to your account</h2>
    {f'<div class="alert alert-error">{error}</div>' if error else ''}
    <form method="POST">
      <label>Email</label><input name="email" type="email" placeholder="your@email.com" required />
      <label>Password</label><input name="password" type="password" placeholder="Your password" required />
      <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;margin-top:4px">Login</button>
    </form>
    <p style="font-size:13px;color:var(--muted);margin-top:12px;text-align:center">New here? <a href="/register" style="color:var(--accent)">Create account</a></p>
  </div>
</main>'''
    return base_html(content, "Login")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    plans = AssemblyPlan.query.filter_by(user_id=current_user.id).order_by(AssemblyPlan.created_at.desc()).all()
    plans_html = ''
    for p in plans:
        plans_html += f'''
        <div class="plan-card">
          <div>
            <div style="font-weight:500;font-size:14px">{p.title}</div>
            <div style="font-size:12px;color:var(--muted);margin-top:2px">{p.date or 'No date'} &nbsp;·&nbsp; {p.class_name or ''} &nbsp;·&nbsp; Theme: {p.theme or '—'}</div>
          </div>
          <div style="display:flex;gap:8px">
            <a href="/plan/{p.id}" class="btn btn-sm btn-outline">Open</a>
            <a href="/delete-plan/{p.id}" class="btn btn-sm btn-danger" onclick="return confirm('Delete this plan?')">Delete</a>
          </div>
        </div>'''
    if not plans:
        plans_html = '<div style="text-align:center;padding:2rem;color:var(--muted);font-size:13px">No plans yet. Create your first one!</div>'
    content = f'''
<main>
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;flex-wrap:wrap;gap:10px">
    <div>
      <div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:700">Welcome, {current_user.name.split()[0]}! 👋</div>
      <div style="font-size:13px;color:var(--muted)">{current_user.school or 'Your school'}</div>
    </div>
    <a href="/new-plan" class="btn btn-primary">+ New Assembly Plan</a>
  </div>
  <div style="background:linear-gradient(135deg,rgba(124,58,237,0.15),rgba(167,139,250,0.1));border:1px solid rgba(167,139,250,0.3);border-radius:12px;padding:1rem 1.25rem;margin-bottom:1.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px"><div><div style="font-size:14px;font-weight:500">🌍 Help improve this app!</div><div style="font-size:12px;color:var(--muted);margin-top:2px">Share your feedback — takes just 2 minutes. Your suggestions shape future features.</div></div><a href="https://forms.gle/MeaBkvtQ1r6FDQPbA" target="_blank" class="btn btn-primary btn-sm">💬 Give Feedback</a></div>
  <div class="card">
    <h2>Your Assembly Plans ({len(plans)})</h2>
    {plans_html}
  </div>
</main>'''
    return base_html(content, "Dashboard")

# ── New Plan ─────────────────────────────────────────────────────────────────

@app.route('/new-plan', methods=['GET','POST'])
@login_required
def new_plan():
    if request.method == 'POST':
        # Build class name
        class_num = request.form.get('class_num', '')
        section = request.form.get('section', '').strip()
        custom_section = request.form.get('custom_section', '').strip()
        if custom_section:
            section = custom_section
        if class_num in ['11', '12']:
            class_display = f'Class {class_num}'
        elif section:
            class_display = f'Class {class_num} {section}'
        else:
            class_display = f'Class {class_num}'

        # Build slots from form order
        slot_names = request.form.getlist('slot_name[]')
        slot_durs = request.form.getlist('slot_dur[]')
        slots = []
        for n, d in zip(slot_names, slot_durs):
            if n.strip():
                try:
                    dur = int(d)
                except:
                    dur = 3
                slots.append({'name': n.strip(), 'dur': dur})

        if not slots:
            slots = [
                {"name":"March in & Prayer","dur":3},
                {"name":"National Anthem","dur":2},
                {"name":"Thought for the Day","dur":2},
                {"name":"Current Affairs","dur":3},
                {"name":"Theme Speech","dur":5},
                {"name":"Quiz","dur":5},
                {"name":"Teacher's Address","dur":5},
                {"name":"Announcements","dur":2},
                {"name":"Dispersal","dur":1}
            ]

        plan = AssemblyPlan(
            user_id=current_user.id,
            title=request.form.get('title','Untitled Plan'),
            date=request.form.get('date',''),
            theme=request.form.get('theme',''),
            class_name=class_display,
            venue=request.form.get('venue',''),
            start_time=request.form.get('start_time','07:30'),
            slots=json.dumps(slots),
            students=json.dumps([])
        )
        db.session.add(plan)
        db.session.commit()
        return redirect(url_for('view_plan', plan_id=plan.id))

    default_slots = [
        {"name":"March in & Prayer","dur":3},
        {"name":"National Anthem","dur":2},
        {"name":"Thought for the Day","dur":2},
        {"name":"Current Affairs","dur":3},
        {"name":"Theme Speech","dur":5},
        {"name":"Quiz","dur":5},
        {"name":"Teacher's Address","dur":5},
        {"name":"Announcements","dur":2},
        {"name":"Dispersal","dur":1}
    ]
    default_slots_inputs = ''
    for i, s in enumerate(default_slots):
        default_slots_inputs += f'''
        <div class="slot-item" data-index="{i}">
          <span class="drag-handle">⠿</span>
          <input type="hidden" name="slot_name[]" value="{s['name']}" class="slot-name-hidden"/>
          <div style="flex:1;font-size:13px" class="slot-label">{s['name']}</div>
          <input type="number" name="slot_dur[]" value="{s['dur']}" min="1" max="60" class="slot-dur-input" style="width:55px;margin:0"/>
          <span style="font-size:11px;color:var(--muted)">min</span>
          <button type="button" onclick="removeSlotRow(this)" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:14px;padding:0 4px">✕</button>
        </div>'''

    content = f'''
<main style="max-width:680px">
  <div style="margin-bottom:1.5rem">
    <a href="/dashboard" style="color:var(--muted);text-decoration:none;font-size:13px">← Back to dashboard</a>
    <div style="font-family:Syne,sans-serif;font-size:1.3rem;font-weight:700;margin-top:8px">Create New Assembly Plan</div>
  </div>

  <form method="POST" id="plan-form">

    <!-- Basic Info -->
    <div class="card">
      <h2>📋 Basic Details</h2>
      <label>Plan title</label><input name="title" placeholder="e.g. Monday Assembly — Week 3" required />
      <div class="grid-2">
        <div><label>Date</label><input name="date" type="date" /></div>
        <div><label>Start time</label><input name="start_time" type="time" value="07:30" /></div>
      </div>
      <label>Weekly theme</label><input name="theme" placeholder="e.g. Technology and AI, Environment Day..." />
      <div class="grid-2">
        <div><label>Venue</label>
          <select name="venue">
            <option>Main Ground</option><option>Assembly Hall</option>
            <option>Auditorium</option><option>Corridor</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Class & Section -->
    <div class="card">
      <h2>🏫 Class & Section</h2>
      <div class="grid-2">
        <div>
          <label>Class</label>
          <select name="class_num" id="class-num-select" onchange="updateSections()">
            <option value="">— Select Class —</option>
            {''.join([f'<option value="{i}">{i}</option>' for i in range(1,13)])}
          </select>
        </div>
        <div id="section-box">
          <label>Section</label>
          <select name="section" id="section-select">
            <option value="">— Select Class first —</option>
          </select>
        </div>
      </div>
      <div id="custom-section-box" style="display:none">
        <label>Or type custom section name (e.g. X1, Blue, Rose)</label>
        <input name="custom_section" id="custom-section-input" placeholder="e.g. X1" style="margin-bottom:0"/>
      </div>
    </div>

    <!-- Assembly Sequence -->
    <div class="card">
      <h2>📝 Assembly Sequence <span style="font-size:12px;color:var(--muted);font-weight:400">— drag to reorder, edit duration</span></h2>
      <div style="margin-bottom:12px">
        <span style="font-size:12px;color:var(--muted)">Quick add:</span><br/>
        <button type="button" class="slot-template-btn" onclick="addTemplateSlot('PT / Exercise', 5)">+ PT / Exercise</button>
        <button type="button" class="slot-template-btn" onclick="addTemplateSlot('Cultural Programme', 5)">+ Cultural Programme</button>
        <button type="button" class="slot-template-btn" onclick="addTemplateSlot('News Reading', 3)">+ News Reading</button>
        <button type="button" class="slot-template-btn" onclick="addTemplateSlot('Pledge', 2)">+ Pledge</button>
        <button type="button" class="slot-template-btn" onclick="addTemplateSlot('Value Education', 5)">+ Value Education</button>
        <button type="button" class="slot-template-btn" onclick="addTemplateSlot('Birthday Wishes', 2)">+ Birthday Wishes</button>
      </div>
      <div id="slots-sortable">
        {default_slots_inputs}
      </div>
      <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;align-items:center">
        <input id="new-slot-name" placeholder="Add custom slot" style="flex:1;min-width:120px;margin:0"/>
        <input type="number" id="new-slot-dur" value="3" min="1" max="60" style="width:60px;margin:0"/>
        <span style="font-size:12px;color:var(--muted)">min</span>
        <button type="button" class="btn btn-outline btn-sm" onclick="addCustomSlot()">+ Add</button>
      </div>
    </div>

    <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">Create Plan →</button>
  </form>
</main>

<script>
// Section logic
function updateSections() {{
  const cls = parseInt(document.getElementById('class-num-select').value);
  const sel = document.getElementById('section-select');
  const customBox = document.getElementById('custom-section-box');
  sel.innerHTML = '';
  if (!cls) {{ sel.innerHTML = '<option value="">— Select Class first —</option>'; return; }}
  const sections = ['A','B','C','D','E','F','G','H'];
  sel.innerHTML = '<option value="">— Select Section —</option>';
  sections.forEach(s => {{ sel.innerHTML += `<option value="${{s}}">${{s}}</option>`; }});
  sel.innerHTML += '<option value="__custom__">Other (type below)</option>';
  customBox.style.display = 'none';
  sel.onchange = function() {{
    customBox.style.display = this.value === '__custom__' ? 'block' : 'none';
  }};
}}

// Drag & drop for slots
const sortable = new Sortable(document.getElementById('slots-sortable'), {{
  animation: 150,
  handle: '.drag-handle',
  onEnd: updateSlotNumbers
}});

function updateSlotNumbers() {{
  // sync hidden inputs with visible labels after drag
  const items = document.querySelectorAll('#slots-sortable .slot-item');
  items.forEach((item, i) => {{
    const hidden = item.querySelector('.slot-name-hidden');
    const label = item.querySelector('.slot-label');
    if (hidden && label) hidden.value = label.textContent;
  }});
}}

function removeSlotRow(btn) {{
  btn.closest('.slot-item').remove();
}}

function addTemplateSlot(name, dur) {{
  addSlotRow(name, dur);
}}

function addCustomSlot() {{
  const name = document.getElementById('new-slot-name').value.trim();
  const dur = parseInt(document.getElementById('new-slot-dur').value) || 3;
  if (!name) return;
  addSlotRow(name, dur);
  document.getElementById('new-slot-name').value = '';
}}

function addSlotRow(name, dur) {{
  const container = document.getElementById('slots-sortable');
  const div = document.createElement('div');
  div.className = 'slot-item';
  div.innerHTML = `
    <span class="drag-handle">⠿</span>
    <input type="hidden" name="slot_name[]" value="${{name}}" class="slot-name-hidden"/>
    <div style="flex:1;font-size:13px" class="slot-label">${{name}}</div>
    <input type="number" name="slot_dur[]" value="${{dur}}" min="1" max="60" class="slot-dur-input" style="width:55px;margin:0"/>
    <span style="font-size:11px;color:var(--muted)">min</span>
    <button type="button" onclick="removeSlotRow(this)" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:14px;padding:0 4px">✕</button>
  `;
  container.appendChild(div);
}}

// Before submit: sync all hidden slot name inputs from labels
document.getElementById('plan-form').addEventListener('submit', function() {{
  document.querySelectorAll('#slots-sortable .slot-item').forEach(item => {{
    const hidden = item.querySelector('.slot-name-hidden');
    const label = item.querySelector('.slot-label');
    if (hidden && label) hidden.value = label.textContent.trim();
  }});
}});
</script>'''
    return base_html(content, "New Plan")

# ── View/Edit Plan ────────────────────────────────────────────────────────────

@app.route('/plan/<int:plan_id>')
@login_required
def view_plan(plan_id):
    plan = AssemblyPlan.query.get_or_404(plan_id)
    if plan.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    slots = json.loads(plan.slots)
    students = json.loads(plan.students)
    total_dur = sum(s['dur'] for s in slots)
    slot_names = [s['name'] for s in slots]

    slots_html = ''
    for i, s in enumerate(slots):
        slots_html += f'''<div class="slot-item" data-slot="{s['name']}">
          <span class="drag-handle">⠿</span>
          <div class="slot-num">{i+1}</div>
          <div style="flex:1;font-size:13px">{s['name']}</div>
          <input type="number" class="slot-dur-input" value="{s['dur']}" min="1" max="60"
            onchange="updateSlotDur({plan.id}, '{s['name']}', this.value)" />
          <span style="font-size:11px;color:var(--muted)">min</span>
          <button onclick="removeSlot({plan.id}, '{s['name']}')" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:14px;padding:0 4px">✕</button>
        </div>'''

    def student_row(s, pid):
        n = s['name'].replace("'", "\\'")
        return f'<div class="slot-item"><div style="flex:1;font-size:13px">{s["name"]}</div><span class="tag purple">{s["cls"]}</span><span class="tag">{s["role"]}</span><button onclick="removeStudent({pid}, \'{n}\')" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:14px;padding:0 4px">✕</button></div>'
    students_html = ''.join([student_row(s, plan.id) for s in students]) if students else '<div style="font-size:13px;color:var(--muted);padding:8px 0">No students assigned yet.</div>'

    slot_options = ''.join([f'<option>{n}</option>' for n in slot_names])

    content = f'''
<main>
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;flex-wrap:wrap;gap:10px">
    <div>
      <a href="/dashboard" style="color:var(--muted);text-decoration:none;font-size:13px">← Dashboard</a>
      <div style="font-family:Syne,sans-serif;font-size:1.3rem;font-weight:700;margin-top:4px">{plan.title}</div>
      <div style="font-size:12px;color:var(--muted)">{plan.date or ''} &nbsp;·&nbsp; {plan.class_name} &nbsp;·&nbsp; {plan.venue} &nbsp;·&nbsp; Theme: {plan.theme or "—"} &nbsp;·&nbsp; Total: {total_dur} mins</div>
    </div>
    <button onclick="window.print()" class="btn btn-outline btn-sm">🖨️ Print</button>
  </div>

  <div class="grid-2">
    <!-- Slots -->
    <div class="card">
      <h2>Programme Slots <span style="font-size:11px;color:var(--muted);font-weight:400">drag to reorder</span></h2>
      <div id="slots-sortable">{slots_html}</div>
      <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;align-items:center">
        <input id="new-slot" placeholder="Add slot name" style="flex:1;min-width:100px;margin:0" />
        <input type="number" id="new-dur" value="3" min="1" max="60" style="width:55px;margin:0"/>
        <span style="font-size:11px;color:var(--muted)">min</span>
        <button class="btn btn-outline btn-sm" onclick="addSlot({plan.id})">+ Add</button>
      </div>
    </div>

    <!-- Students -->
    <div class="card">
      <h2>Student Roles</h2>
      <div id="students-list">{students_html}</div>
      <div style="margin-top:10px">
        <input id="new-student" placeholder="Student name" style="margin-bottom:6px" />
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <input id="new-cls" placeholder="Class e.g. X A" style="flex:1;min-width:80px;margin:0"/>
          <select id="new-role" style="flex:1;min-width:120px;margin:0">{slot_options}</select>
          <button class="btn btn-outline btn-sm" onclick="addStudent({plan.id})">+ Add</button>
        </div>
      </div>
    </div>
  </div>

  <!-- AI Content Generator -->
  <div class="card">
    <h2>🤖 AI Content Generator</h2>
    <div style="font-size:13px;color:var(--muted);margin-bottom:12px">Generate ready-to-use assembly content based on your theme: <strong style="color:var(--accent)">{plan.theme or "General"}</strong></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
      <button class="btn btn-outline btn-sm" id="btn-speech" onclick="generate({plan.id},'speech',this)">📝 Theme Speech</button>
      <button class="btn btn-outline btn-sm" id="btn-thought" onclick="generate({plan.id},'thought',this)">💭 Thought for the Day</button>
      <button class="btn btn-outline btn-sm" id="btn-quiz" onclick="generate({plan.id},'quiz',this)">❓ Quiz Questions</button>
      <button class="btn btn-outline btn-sm" id="btn-mc" onclick="generate({plan.id},'mc',this)">🎤 MC Script</button>
      <button class="btn btn-outline btn-sm" id="btn-news" onclick="generate({plan.id},'news',this)">📰 Current Affairs</button>
    </div>
    <div id="ai-label" style="font-size:11px;color:var(--muted);margin-bottom:4px;display:none"></div>
    <div id="ai-loading" style="display:none;font-size:13px;color:var(--muted);padding:8px 0">⏳ Generating content, please wait...</div>
    <div id="ai-output" class="ai-output"></div>
    <div style="display:flex;gap:8px;margin-top:8px;display:none" id="ai-actions">
      <button class="btn btn-green btn-sm" onclick="copyAI()">📋 Copy</button>
    </div>
  </div>

  <!-- Run Sheet -->
  <div class="card no-print">
    <h2>📋 Run Sheet</h2>
    <div id="runsheet">{generate_runsheet(slots, students, plan.start_time)}</div>
  </div>

  <!-- Print version -->
  <div class="print-area">
    <h1 style="font-size:18px;margin-bottom:4px">{plan.title}</h1>
    <p style="font-size:12px;color:#666;margin-bottom:12px">{plan.date} · {plan.class_name} · {plan.venue} · Theme: {plan.theme}</p>
    {generate_runsheet_print(slots, students, plan.start_time)}
  </div>
</main>

<script>
// Drag to reorder slots
const sortable = new Sortable(document.getElementById('slots-sortable'), {{
  animation: 150,
  handle: '.drag-handle',
  onEnd: function() {{ saveSlotOrder({plan.id}); }}
}});

async function saveSlotOrder(planId) {{
  const items = document.querySelectorAll('#slots-sortable .slot-item');
  const order = Array.from(items).map(el => el.dataset.slot);
  await fetch('/api/reorder-slots', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan_id:planId,order}})}});
  location.reload();
}}

async function updateSlotDur(planId, name, dur) {{
  await fetch('/api/update-slot-dur', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan_id:planId,name,dur:parseInt(dur)}})}});
  location.reload();
}}

async function removeSlot(planId, name) {{
  if (!confirm('Remove this slot?')) return;
  await fetch('/api/remove-slot', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan_id:planId,name}})}});
  location.reload();
}}

async function addSlot(planId) {{
  const name = document.getElementById('new-slot').value.trim();
  const dur = parseInt(document.getElementById('new-dur').value) || 3;
  if (!name) return;
  const res = await fetch('/api/add-slot', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan_id:planId,name,dur}})}});
  if (res.ok) location.reload();
}}

async function addStudent(planId) {{
  const name = document.getElementById('new-student').value.trim();
  const cls = document.getElementById('new-cls').value.trim();
  const role = document.getElementById('new-role').value;
  if (!name) return;
  const res = await fetch('/api/add-student', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan_id:planId,name,cls,role}})}});
  if (res.ok) location.reload();
}}

async function removeStudent(planId, name) {{
  await fetch('/api/remove-student', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan_id:planId,name}})}});
  location.reload();
}}

const typeLabels = {{
  speech: '📝 Theme Speech',
  thought: '💭 Thought for the Day',
  quiz: '❓ Quiz Questions',
  mc: '🎤 MC Script',
  news: '📰 Current Affairs'
}};

async function generate(planId, type, btn) {{
  // Disable all buttons
  document.querySelectorAll('[id^="btn-"]').forEach(b => b.disabled = true);
  document.getElementById('ai-loading').style.display = 'block';
  document.getElementById('ai-label').style.display = 'none';
  document.getElementById('ai-output').classList.remove('visible');
  document.getElementById('ai-actions').style.display = 'none';

  try {{
    const res = await fetch('/api/generate', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{plan_id:planId,type}})
    }});
    const data = await res.json();
    document.getElementById('ai-loading').style.display = 'none';
    const label = document.getElementById('ai-label');
    label.textContent = typeLabels[type] || type;
    label.style.display = 'block';
    const out = document.getElementById('ai-output');
    out.textContent = data.content || data.error || 'Could not generate content.';
    out.classList.add('visible');
    document.getElementById('ai-actions').style.display = 'flex';
  }} catch(e) {{
    document.getElementById('ai-loading').style.display = 'none';
    const out = document.getElementById('ai-output');
    out.textContent = 'Network error. Please try again.';
    out.classList.add('visible');
  }}
  document.querySelectorAll('[id^="btn-"]').forEach(b => b.disabled = false);
}}

function copyAI() {{
  navigator.clipboard.writeText(document.getElementById('ai-output').textContent);
  alert('Copied to clipboard!');
}}
</script>'''
    return base_html(content, plan.title)

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_time(mins):
    h = (mins // 60) % 24
    m = mins % 60
    ampm = 'PM' if h >= 12 else 'AM'
    h = h % 12 or 12
    return f"{h}:{str(m).zfill(2)} {ampm}"

def parse_time(t):
    try:
        h, m = map(int, t.split(':'))
        return h * 60 + m
    except:
        return 7 * 60 + 30

def generate_runsheet(slots, students, start_time):
    cur = parse_time(start_time or '07:30')
    html = '<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="border-bottom:1px solid var(--border2)"><th style="text-align:left;padding:6px 8px;color:var(--muted);font-size:11px">TIME</th><th style="text-align:left;padding:6px 8px;color:var(--muted);font-size:11px">SLOT</th><th style="text-align:left;padding:6px 8px;color:var(--muted);font-size:11px">DUR</th><th style="text-align:left;padding:6px 8px;color:var(--muted);font-size:11px">ASSIGNED TO</th></tr></thead><tbody>'
    for s in slots:
        assigned = [st['name'] for st in students if st['role'] == s['name']]
        html += f'<tr style="border-bottom:1px solid var(--border)"><td style="padding:7px 8px;white-space:nowrap">{fmt_time(cur)}</td><td style="padding:7px 8px">{s["name"]}</td><td style="padding:7px 8px;color:var(--muted)">{s["dur"]}m</td><td style="padding:7px 8px">{", ".join(assigned) or "—"}</td></tr>'
        cur += s['dur']
    html += f'<tr><td style="padding:7px 8px;color:var(--muted)" colspan="4">End: {fmt_time(cur)}</td></tr></tbody></table>'
    return html

def generate_runsheet_print(slots, students, start_time):
    cur = parse_time(start_time or '07:30')
    html = '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr><th style="text-align:left;padding:4px 6px;border-bottom:1px solid #ccc">Time</th><th style="text-align:left;padding:4px 6px;border-bottom:1px solid #ccc">Slot</th><th style="text-align:left;padding:4px 6px;border-bottom:1px solid #ccc">Duration</th><th style="text-align:left;padding:4px 6px;border-bottom:1px solid #ccc">Assigned to</th></tr></thead><tbody>'
    for s in slots:
        assigned = [st['name'] for st in students if st['role'] == s['name']]
        html += f'<tr style="border-bottom:1px solid #eee"><td style="padding:5px 6px">{fmt_time(cur)}</td><td style="padding:5px 6px">{s["name"]}</td><td style="padding:5px 6px">{s["dur"]} min</td><td style="padding:5px 6px">{", ".join(assigned) or "—"}</td></tr>'
        cur += s['dur']
    html += '</tbody></table>'
    return html

# ── API Routes ────────────────────────────────────────────────────────────────

@app.route('/api/add-slot', methods=['POST'])
@login_required
def api_add_slot():
    data = request.json
    plan = AssemblyPlan.query.get_or_404(data['plan_id'])
    if plan.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    slots = json.loads(plan.slots)
    slots.append({'name': data['name'], 'dur': data['dur']})
    plan.slots = json.dumps(slots)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/remove-slot', methods=['POST'])
@login_required
def api_remove_slot():
    data = request.json
    plan = AssemblyPlan.query.get_or_404(data['plan_id'])
    if plan.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    slots = json.loads(plan.slots)
    slots = [s for s in slots if s['name'] != data['name']]
    plan.slots = json.dumps(slots)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/reorder-slots', methods=['POST'])
@login_required
def api_reorder_slots():
    data = request.json
    plan = AssemblyPlan.query.get_or_404(data['plan_id'])
    if plan.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    slots = json.loads(plan.slots)
    order = data['order']
    slot_map = {s['name']: s for s in slots}
    new_slots = [slot_map[name] for name in order if name in slot_map]
    plan.slots = json.dumps(new_slots)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/update-slot-dur', methods=['POST'])
@login_required
def api_update_slot_dur():
    data = request.json
    plan = AssemblyPlan.query.get_or_404(data['plan_id'])
    if plan.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    slots = json.loads(plan.slots)
    for s in slots:
        if s['name'] == data['name']:
            s['dur'] = data['dur']
    plan.slots = json.dumps(slots)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/add-student', methods=['POST'])
@login_required
def api_add_student():
    data = request.json
    plan = AssemblyPlan.query.get_or_404(data['plan_id'])
    if plan.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    students = json.loads(plan.students)
    students.append({'name': data['name'], 'cls': data['cls'], 'role': data['role']})
    plan.students = json.dumps(students)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/remove-student', methods=['POST'])
@login_required
def api_remove_student():
    data = request.json
    plan = AssemblyPlan.query.get_or_404(data['plan_id'])
    if plan.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    students = json.loads(plan.students)
    students = [s for s in students if s['name'] != data['name']]
    plan.students = json.dumps(students)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/generate', methods=['POST'])
@login_required
def api_generate():
    data = request.json
    plan = AssemblyPlan.query.get_or_404(data['plan_id'])
    if plan.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    api_key = GROQ_API_KEY
    if not api_key:
        return jsonify({'error': 'Groq API key not configured on server'}), 500

    theme = plan.theme or 'General'
    cls = plan.class_name or 'Class IX-XII'
    content_type = data.get('type', 'speech')

    prompts = {
        'speech': f'Write a 2-minute morning assembly speech for a {cls} student in an Indian CBSE school. Theme: {theme}. Formal English, inspiring, age-appropriate. Ready to deliver.',
        'thought': f'Write 3 original Thoughts for the Day for a CBSE school morning assembly. Theme: {theme}. Each thought: one quote + 2 sentence explanation. Number them 1, 2, 3.',
        'quiz': f'Write 5 quiz questions with answers for a CBSE school morning assembly. Theme: {theme}. Suitable for {cls} students. Format: Q1: question / A1: answer',
        'mc': f'Write a complete MC/anchor script for a CBSE school morning assembly. Theme: {theme}. Class: {cls}. Include welcome, transitions between: Prayer, Anthem, Thought for the Day, Speech, Quiz, Teacher Address, Vote of Thanks. Formal but warm tone.',
        'news': f'Write 5 current affairs points for a CBSE school morning assembly. Theme connection: {theme}. Format for {cls} students. Include India news, world news, science/tech. Simple English. Ready to read aloud.'
    }

    prompt = prompts.get(content_type, prompts['speech'])

    try:
        res = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json={
                'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
                'max_tokens': 800,
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=45
        )
        result = res.json()
        if 'error' in result:
            return jsonify({'error': f"API error: {result['error'].get('message', 'Unknown error')}"}), 500
        content = result['choices'][0]['message']['content']
        return jsonify({'content': content})
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timed out. Please try again.'}), 500
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/delete-plan/<int:plan_id>')
@login_required
def delete_plan(plan_id):
    plan = AssemblyPlan.query.get_or_404(plan_id)
    if plan.user_id == current_user.id:
        db.session.delete(plan)
        db.session.commit()
    return redirect(url_for('dashboard'))

# ── Init ──────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
