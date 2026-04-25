import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link } from 'react-router-dom';
import { loginUser } from '../store/slices/authSlice';

const Login = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error, token } = useSelector((state) => state.auth);
  const [form, setForm] = useState({ email: '', password: '' });
  const [longLoading, setLongLoading] = useState(false);

  useEffect(() => {
    if (token) navigate('/dashboard');
  }, [token, navigate]);

  useEffect(() => {
    let timer;
    if (loading) {
      timer = setTimeout(() => {
        setLongLoading(true);
      }, 3000); // Trigger after 3 seconds
    } else {
      setLongLoading(false);
    }
    return () => clearTimeout(timer);
  }, [loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    dispatch(loginUser(form));
  };

  return (
    <div className="auth-container">
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <div className="auth-card">
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <span style={{ fontSize: '48px' }}>💊</span>
          <h1 style={titleStyle}>HCP CRM</h1>
          <p style={{ color: '#6b7280', fontSize: '14px' }}>Sign in to your account</p>
        </div>

        {error && (
          <div style={errorStyle}>⚠️ {error}</div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={fieldStyle}>
            <label style={labelStyle}>Email</label>
            <input
              type="email"
              placeholder="Enter your email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              style={inputStyle}
              required
            />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Password</label>
            <input
              type="password"
              placeholder="Enter your password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              style={inputStyle}
              required
            />
          </div>

          <button type="submit" style={btnStyle} disabled={loading}>
            {loading 
              ? (longLoading ? '⏳ Waking up free server (approx 45s)...' : '⏳ Signing in...') 
              : '🔐 Sign In'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '24px', color: '#6b7280', fontSize: '14px' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: '#667eea', fontWeight: '600', textDecoration: 'none' }}>
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
};



const titleStyle = {
  fontSize: '28px',
  fontWeight: '700',
  color: '#1f2937',
  margin: '8px 0 4px',
};

const fieldStyle = {
  marginBottom: '20px',
};

const labelStyle = {
  display: 'block',
  fontSize: '14px',
  fontWeight: '500',
  color: '#374151',
  marginBottom: '6px',
};

const inputStyle = {
  width: '100%',
  padding: '12px 16px',
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  fontSize: '14px',
  fontFamily: 'Inter, sans-serif',
  outline: 'none',
  boxSizing: 'border-box',
  transition: 'border 0.2s',
};

const btnStyle = {
  width: '100%',
  padding: '13px',
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  fontSize: '16px',
  fontWeight: '600',
  cursor: 'pointer',
  fontFamily: 'Inter, sans-serif',
  marginTop: '8px',
};

const errorStyle = {
  background: '#fee2e2',
  color: '#dc2626',
  padding: '12px',
  borderRadius: '8px',
  fontSize: '14px',
  marginBottom: '20px',
};

export default Login;