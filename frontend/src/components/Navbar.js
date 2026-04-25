import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../store/slices/authSlice';

const Navbar = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const user = useSelector((state) => state.auth.user);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  return (
    <nav className="navbar-container" style={{
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      fontFamily: 'Inter, sans-serif',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '24px' }}>💊</span>
        <span style={{ color: 'white', fontWeight: '700', fontSize: '20px' }}>HCP CRM</span>
      </div>

      <div className="navbar-links">
        <button onClick={() => navigate('/dashboard')} style={navBtnStyle}>
          📊 Dashboard
        </button>
        <button onClick={() => navigate('/log')} style={navBtnStyle}>
          ➕ Log Interaction
        </button>
        {user && (
          <span style={{ color: 'white', fontSize: '14px' }}>
            👤 {user.name}
          </span>
        )}
        <button onClick={handleLogout} style={{
          ...navBtnStyle,
          background: 'rgba(255,255,255,0.2)',
          border: '1px solid rgba(255,255,255,0.4)',
        }}>
          🚪 Logout
        </button>
      </div>
    </nav>
  );
};

const navBtnStyle = {
  background: 'transparent',
  border: 'none',
  color: 'white',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: '500',
  padding: '8px 12px',
  borderRadius: '8px',
  transition: 'background 0.2s',
  fontFamily: 'Inter, sans-serif',
};

export default Navbar;