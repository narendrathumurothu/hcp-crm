import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { fetchInteractions, deleteInteraction } from '../store/slices/interactionSlice';
import Navbar from '../components/Navbar';
import API from '../api/axios';

const Dashboard = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { list, loading } = useSelector((state) => state.interactions);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    dispatch(fetchInteractions());
    API.get('/api/stats').then((res) => setStats(res.data));
  }, [dispatch]);

  const handleDelete = (id) => {
    if (window.confirm('Delete this interaction?')) {
      dispatch(deleteInteraction(id));
    }
  };

  const handleSearch = async () => {
    if (!search.trim()) return;
    const res = await API.get(`/api/search?q=${search}`);
    setSearchResults(res.data.results);
  };

  const displayList = searchResults || list;

  const getSentimentColor = (sentiment) => {
    if (sentiment === 'Positive') return '#10b981';
    if (sentiment === 'Negative') return '#ef4444';
    return '#f59e0b';
  };

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', minHeight: '100vh', background: '#f3f4f6' }}>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <Navbar />

      <div style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>

        {/* Stats Cards */}
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
            <div style={statCardStyle('#667eea')}>
              <div style={{ fontSize: '32px', fontWeight: '700', color: 'white' }}>{stats.total_interactions}</div>
              <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px' }}>Total Interactions</div>
            </div>
            <div style={statCardStyle('#10b981')}>
              <div style={{ fontSize: '32px', fontWeight: '700', color: 'white' }}>{stats.sentiment_breakdown?.Positive || 0}</div>
              <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px' }}>Positive</div>
            </div>
            <div style={statCardStyle('#f59e0b')}>
              <div style={{ fontSize: '32px', fontWeight: '700', color: 'white' }}>{stats.sentiment_breakdown?.Neutral || 0}</div>
              <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px' }}>Neutral</div>
            </div>
            <div style={statCardStyle('#ef4444')}>
              <div style={{ fontSize: '32px', fontWeight: '700', color: 'white' }}>{stats.sentiment_breakdown?.Negative || 0}</div>
              <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px' }}>Negative</div>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
          <input
            type="text"
            placeholder="🔍 Search by HCP name, topic, sentiment..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              if (!e.target.value) setSearchResults(null);
            }}
            style={{ ...inputStyle, flex: 1 }}
          />
          <button onClick={handleSearch} style={searchBtnStyle}>Search</button>
          <button onClick={() => navigate('/log')} style={addBtnStyle}>➕ Log Interaction</button>
        </div>

        {/* Interactions List */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>⏳ Loading...</div>
        ) : displayList.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', color: '#6b7280' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
            <p>No interactions found. Log your first interaction!</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {displayList.map((interaction) => (
              <div key={interaction.id} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>
                        👨‍⚕️ {interaction.hcp_name}
                      </h3>
                      <span style={{
                        background: getSentimentColor(interaction.sentiment),
                        color: 'white',
                        padding: '2px 10px',
                        borderRadius: '20px',
                        fontSize: '12px',
                        fontWeight: '500',
                      }}>
                        {interaction.sentiment}
                      </span>
                      <span style={{
                        background: '#e5e7eb',
                        color: '#374151',
                        padding: '2px 10px',
                        borderRadius: '20px',
                        fontSize: '12px',
                      }}>
                        {interaction.interaction_type}
                      </span>
                    </div>

                    {interaction.topics && (
                      <p style={{ margin: '4px 0', color: '#4b5563', fontSize: '14px' }}>
                        📌 <strong>Topics:</strong> {interaction.topics}
                      </p>
                    )}
                    {interaction.outcomes && (
                      <p style={{ margin: '4px 0', color: '#4b5563', fontSize: '14px' }}>
                        ✅ <strong>Outcomes:</strong> {interaction.outcomes}
                      </p>
                    )}
                    {interaction.follow_up_actions && (
                      <p style={{ margin: '4px 0', color: '#4b5563', fontSize: '14px' }}>
                        🔔 <strong>Follow-up:</strong> {interaction.follow_up_actions}
                      </p>
                    )}
                    {interaction.ai_summary && (
                      <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: '13px', fontStyle: 'italic' }}>
                        🤖 {interaction.ai_summary}
                      </p>
                    )}
                    <p style={{ margin: '8px 0 0', color: '#9ca3af', fontSize: '12px' }}>
                      🕐 {new Date(interaction.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', marginLeft: '16px' }}>
                    <button
                      onClick={() => navigate(`/log?edit=${interaction.id}`)}
                      style={editBtnStyle}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={() => handleDelete(interaction.id)}
                      style={deleteBtnStyle}
                    >
                      🗑️ Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const statCardStyle = (color) => ({
  background: `linear-gradient(135deg, ${color} 0%, ${color}cc 100%)`,
  borderRadius: '12px',
  padding: '20px',
  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
});

const cardStyle = {
  background: 'white',
  borderRadius: '12px',
  padding: '20px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  transition: 'box-shadow 0.2s',
};

const inputStyle = {
  padding: '12px 16px',
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  fontSize: '14px',
  fontFamily: 'Inter, sans-serif',
  outline: 'none',
};

const searchBtnStyle = {
  padding: '12px 20px',
  background: '#667eea',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  fontFamily: 'Inter, sans-serif',
  fontWeight: '600',
};

const addBtnStyle = {
  padding: '12px 20px',
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  fontFamily: 'Inter, sans-serif',
  fontWeight: '600',
};

const editBtnStyle = {
  padding: '8px 14px',
  background: '#f3f4f6',
  border: '1px solid #d1d5db',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '13px',
  fontFamily: 'Inter, sans-serif',
};

const deleteBtnStyle = {
  padding: '8px 14px',
  background: '#fee2e2',
  border: '1px solid #fca5a5',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '13px',
  color: '#dc2626',
  fontFamily: 'Inter, sans-serif',
};

export default Dashboard;