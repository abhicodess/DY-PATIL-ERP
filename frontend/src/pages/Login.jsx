import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('admin'); // Default role matching legacy template
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(false);

    try {
      const user = await login(username, password, role);
      if (user.role === 'admin') navigate('/admin');
      else if (user.role === 'faculty') navigate('/faculty');
      else if (user.role === 'student') navigate('/student');
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Invalid username, password, or role');
    }
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  return (
    <div className="lp">
      <div className="lp-left">
        <div className="lp-glow"></div>
        <div className="lp-dots"></div>
        <div className="lp-brand">
          <img src="/static/images/dypatil_logo.png" className="lp-logo" alt="DY Patil University" />
          <div>
            <div className="lp-bname">D Y Patil University</div>
            <div className="lp-bsub">Pune, Ambi — College ERP</div>
          </div>
        </div>
        <div className="lp-tagline">
          <h1>Manage smarter.<br /><span>Educate better.</span></h1>
          <p>A complete academic management system for DY Patil University — students, faculty, and administration in one place.</p>
        </div>
        <div className="lp-stats">
          <div><div className="lp-sv">1,240+</div><div className="lp-sl">Students</div></div>
          <div><div className="lp-sv">48</div><div className="lp-sl">Faculty</div></div>
          <div><div className="lp-sv">4</div><div className="lp-sl">Departments</div></div>
        </div>
      </div>
      <div className="lp-right">
        <div className="lp-form">
          <h2>Welcome back 👋</h2>
          <p>Sign in to your account to continue</p>
          <div className="role-row">
            <button 
              type="button" 
              className={`role-pill ${role === 'admin' ? 'on' : ''}`}
              onClick={() => setRole('admin')}
            >
              <i className="fas fa-shield-halved"></i>Admin
            </button>
            <button 
              type="button" 
              className={`role-pill ${role === 'faculty' ? 'on' : ''}`}
              onClick={() => setRole('faculty')}
            >
              <i className="fas fa-chalkboard-user"></i>Faculty
            </button>
            <button 
              type="button" 
              className={`role-pill ${role === 'student' ? 'on' : ''}`}
              onClick={() => setRole('student')}
            >
              <i className="fas fa-user-graduate"></i>Student
            </button>
          </div>

          {error && (
            <div className="al-err">
              <i className="fas fa-exclamation-circle"></i>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="fg">
              <label>Username / Email / PRN Number</label>
              <div className="fi-wrap">
                <input 
                  className="fi" 
                  type="text" 
                  placeholder={role === 'student' ? 'PRN / Roll Number' : role === 'faculty' ? 'Email Address' : 'Admin username'}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required 
                  autoComplete="username" 
                />
                <i className="fi-ico fas fa-user"></i>
              </div>
            </div>
            <div className="fg">
              <label>Password</label>
              <div className="fi-wrap">
                <input 
                  className="fi" 
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required 
                  autoComplete="current-password" 
                />
                <i 
                  className={`fi-ico fi-eye fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`} 
                  onClick={togglePasswordVisibility}
                  style={{ cursor: 'pointer' }}
                ></i>
              </div>
            </div>
            <button type="submit" className="f-btn">
              <i className="fas fa-arrow-right-to-bracket"></i> Sign In
            </button>
          </form>
          <div style={{ textAlign: 'right', marginBottom: '12px' }}>
            <a href="/forgot_password" style={{ fontSize: '12px', color: '#2563EB', textDecoration: 'none', fontWeight: 600 }}>Forgot password?</a>
          </div>
          <div className="f-cred">
            <div className="f-cred-ttl">Demo Credentials</div>
            <div className="f-cred-row"><span>Admin</span><code>admin / admin123</code></div>
            <div className="f-cred-row"><span>Faculty</span><code>email / faculty123</code></div>
            <div className="f-cred-row"><span>Student</span><code>PRN Number / student123</code></div>
          </div>
        </div>
      </div>
    </div>
  );
};
