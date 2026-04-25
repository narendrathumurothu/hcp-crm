import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { createInteraction, updateInteraction, sendChat } from '../store/slices/interactionSlice';
import Navbar from '../components/Navbar';
import API from '../api/axios';

const LogInteraction = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editId = searchParams.get('edit');
  const { loading, chatResponse } = useSelector((state) => state.interactions);

  const [form, setForm] = useState({
    hcp_name: '',
    interaction_type: 'Meeting',
    date: new Date().toISOString().split('T')[0],
    time: new Date().toTimeString().slice(0, 5),
    attendees: '',
    topics: '',
    materials_shared: '',
    samples_distributed: '',
    sentiment: 'Neutral',
    outcomes: '',
    follow_up_actions: '',
  });

  const [chatMsg, setChatMsg] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [saved, setSaved] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isAiRecording, setIsAiRecording] = useState(false);

  useEffect(() => {
    if (editId) {
      API.get(`/api/interactions/${editId}`).then((res) => {
        const d = res.data;
        setForm({
          hcp_name: d.hcp_name || '',
          interaction_type: d.interaction_type || 'Meeting',
          date: d.date || '',
          time: d.time || '',
          attendees: d.attendees || '',
          topics: d.topics || '',
          materials_shared: d.materials_shared || '',
          samples_distributed: d.samples_distributed || '',
          sentiment: d.sentiment || 'Neutral',
          outcomes: d.outcomes || '',
          follow_up_actions: d.follow_up_actions || '',
        });
      });
    }
  }, [editId]);

  useEffect(() => {
    if (chatResponse) {
      const extracted = chatResponse.extracted_data;
      if (extracted) {
        setForm((prev) => ({
          ...prev,
          hcp_name: extracted.hcp_name || prev.hcp_name,
          topics: extracted.topics || prev.topics,
          sentiment: extracted.sentiment || prev.sentiment,
          outcomes: extracted.outcomes || prev.outcomes,
          follow_up_actions: extracted.follow_up_actions || prev.follow_up_actions,
        }));
      }
      if (chatResponse.followup_suggestions) {
        setSuggestions(chatResponse.followup_suggestions);
      }
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'ai',
          text: chatResponse.response || 'Interaction processed!',
        },
      ]);
    }
  }, [chatResponse]);

  const handleChat = () => {
    if (!chatMsg.trim()) return;
    setChatHistory((prev) => [...prev, { role: 'user', text: chatMsg }]);
    dispatch(sendChat(chatMsg));
    setChatMsg('');
  };

  const handleSubmit = async () => {
    if (!form.hcp_name) {
      alert('HCP Name enter చేయండి!');
      return;
    }
    if (editId) {
      await dispatch(updateInteraction({ id: editId, data: form }));
    } else {
      await dispatch(createInteraction(form));
    }
    setSaved(true);
    setTimeout(() => navigate('/dashboard'), 1500);
  };

  const handleVoice = () => {
    if (!('webkitSpeechRecognition' in window)) {
      alert('in your browser voice recognition support is donot available. Please use Chrome on desktop or Android for this feature.');
      return;
    }
    const recognition = new window.webkitSpeechRecognition();
    recognition.lang = 'en-US';
    recognition.start();
    setIsRecording(true);
    recognition.onresult = (e) => {
      const text = e.results[0][0].transcript;
      setForm((prev) => ({ ...prev, topics: prev.topics + ' ' + text }));
      setIsRecording(false);
    };
    recognition.onerror = () => setIsRecording(false);
    recognition.onend = () => setIsRecording(false);
  };

  const handleAiVoice = () => {
    if (!('webkitSpeechRecognition' in window)) {
      alert('Voice recognition is not supported in this browser. Use Chrome.');
      return;
    }
    const recognition = new window.webkitSpeechRecognition();
    recognition.lang = 'en-US'; // English handles medical terms well
    recognition.start();
    setIsAiRecording(true);
    recognition.onresult = (e) => {
      const text = e.results[0][0].transcript;
      setChatHistory((prev) => [...prev, { role: 'user', text: text }]);
      dispatch(sendChat(text));
      setIsAiRecording(false);
    };
    recognition.onerror = () => setIsAiRecording(false);
    recognition.onend = () => setIsAiRecording(false);
  };

  const sentimentColor = {
    Positive: '#10b981',
    Neutral: '#f59e0b',
    Negative: '#ef4444',
  };

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', minHeight: '100vh', background: '#f3f4f6' }}>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <Navbar />

      {saved && (
        <div style={successBanner}>
          ✅ Interaction {editId ? 'updated' : 'saved'} successfully! Redirecting...
        </div>
      )}

      <div className="log-container">

        {/* LEFT - Form */}
        <div style={panelStyle}>
          <h2 style={panelTitle}>
            {editId ? '✏️ Edit HCP Interaction' : '📋 Log HCP Interaction'}
          </h2>

          <div className="form-row">
            <div style={fieldStyle}>
              <label style={labelStyle}>HCP Name *</label>
              <input
                style={inputStyle}
                placeholder="Search or enter HCP name..."
                value={form.hcp_name}
                onChange={(e) => setForm({ ...form, hcp_name: e.target.value })}
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Interaction Type</label>
              <select
                style={inputStyle}
                value={form.interaction_type}
                onChange={(e) => setForm({ ...form, interaction_type: e.target.value })}
              >
                <option>Meeting</option>
                <option>Call</option>
                <option>Email</option>
                <option>Conference</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div style={fieldStyle}>
              <label style={labelStyle}>Date</label>
              <input
                type="date"
                style={inputStyle}
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Time</label>
              <input
                type="time"
                style={inputStyle}
                value={form.time}
                onChange={(e) => setForm({ ...form, time: e.target.value })}
              />
            </div>
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Attendees</label>
            <input
              style={inputStyle}
              placeholder="Enter attendee names..."
              value={form.attendees}
              onChange={(e) => setForm({ ...form, attendees: e.target.value })}
            />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Topics Discussed</label>
            <button
              onClick={handleVoice}
              style={{
                ...voiceBtnStyle,
                background: isRecording ? '#fee2e2' : '#f3f4f6',
                border: `1px solid ${isRecording ? '#fca5a5' : '#d1d5db'}`,
                color: isRecording ? '#dc2626' : '#374151',
              }}
            >
              {isRecording ? '🔴 Recording... (stop కి click)' : '🎙️ Fill with voice Note'}
            </button>
            <textarea
              style={textareaStyle}
              placeholder="Enter key discussion points..."
              value={form.topics}
              onChange={(e) => setForm({ ...form, topics: e.target.value })}
            />
          </div>

          <div className="form-row">
            <div style={fieldStyle}>
              <label style={labelStyle}>Materials Shared</label>
              <input
                style={inputStyle}
                placeholder="Brochures, PDFs shared..."
                value={form.materials_shared}
                onChange={(e) => setForm({ ...form, materials_shared: e.target.value })}
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Samples Distributed</label>
              <input
                style={inputStyle}
                placeholder="Sample kits given..."
                value={form.samples_distributed}
                onChange={(e) => setForm({ ...form, samples_distributed: e.target.value })}
              />
            </div>
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>HCP Sentiment</label>
            <div className="sentiment-options">
              {['Positive', 'Neutral', 'Negative'].map((s) => (
                <label
                  key={s}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    border: `2px solid ${form.sentiment === s ? sentimentColor[s] : '#e5e7eb'}`,
                    background: form.sentiment === s ? sentimentColor[s] + '20' : 'white',
                    fontSize: '14px',
                    fontWeight: form.sentiment === s ? '600' : '400',
                    color: form.sentiment === s ? sentimentColor[s] : '#6b7280',
                  }}
                >
                  <input
                    type="radio"
                    name="sentiment"
                    value={s}
                    checked={form.sentiment === s}
                    onChange={() => setForm({ ...form, sentiment: s })}
                    style={{ display: 'none' }}
                  />
                  {s === 'Positive' ? '😊' : s === 'Neutral' ? '😐' : '😔'} {s}
                </label>
              ))}
            </div>
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Outcomes</label>
            <textarea
              style={textareaStyle}
              placeholder="Key outcomes or agreements..."
              value={form.outcomes}
              onChange={(e) => setForm({ ...form, outcomes: e.target.value })}
            />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Follow-up Actions</label>
            <textarea
              style={textareaStyle}
              placeholder="Next steps or tasks..."
              value={form.follow_up_actions}
              onChange={(e) => setForm({ ...form, follow_up_actions: e.target.value })}
            />
          </div>

          {suggestions.length > 0 && (
            <div style={{ marginBottom: '16px', padding: '12px', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
              <div style={{ fontSize: '13px', fontWeight: '600', color: '#166534', marginBottom: '8px' }}>
                🤖 AI Suggested Follow-ups:
              </div>
              {suggestions.map((s, i) => (
                <div
                  key={i}
                  style={{ fontSize: '13px', color: '#166534', marginBottom: '4px', cursor: 'pointer' }}
                  onClick={() => setForm((prev) => ({ ...prev, follow_up_actions: prev.follow_up_actions + (prev.follow_up_actions ? '\n' : '') + s }))}
                >
                  ➕ {s}
                </div>
              ))}
            </div>
          )}

          <button onClick={handleSubmit} style={submitBtnStyle} disabled={loading}>
            {loading ? '⏳ Saving...' : editId ? '✅ Update Interaction' : '💾 Save Interaction'}
          </button>
        </div>

        {/* RIGHT - AI Chat */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={panelStyle}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }}></div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#1f2937' }}>AI Assistant</div>
                <div style={{ fontSize: '11px', color: '#9ca3af' }}>Log interaction via chat</div>
              </div>
            </div>

            <div style={{ minHeight: '280px', maxHeight: '280px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
              {chatHistory.length === 0 && (
                <div style={hintStyle}>
                  💬 Tell about interaction with chat:<br />
                  <span style={{ color: '#667eea', fontStyle: 'italic' }}>
                    "I met Dr. Reddy yesterday. We discussed the new hypertension drug. He seemed positive and asked for more brochures. I need to follow up with an email and send the sample kit."
                  </span>
                </div>
              )}
              {chatHistory.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    padding: '8px 12px',
                    borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                    background: msg.role === 'user' ? '#667eea' : '#f3f4f6',
                    color: msg.role === 'user' ? 'white' : '#1f2937',
                    alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: '90%',
                    fontSize: '13px',
                    lineHeight: '1.5',
                  }}
                >
                  {msg.text}
                </div>
              ))}
              {loading && (
                <div style={{ fontSize: '13px', color: '#9ca3af', fontStyle: 'italic' }}>
                  🤖 AI processing...
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <textarea
                style={{ ...inputStyle, flex: 1, height: '40px', resize: 'none', fontSize: '12px' }}
                placeholder="Describe interaction..."
                value={chatMsg}
                onChange={(e) => setChatMsg(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleChat(); } }}
              />
              <button 
                onClick={handleAiVoice} 
                style={{
                  ...chatBtnStyle, 
                  background: isAiRecording ? '#ef4444' : '#10b981',
                  padding: '8px 12px'
                }}
                title="Speak to AI"
              >
                {isAiRecording ? '🛑' : '🎙️ AI'}
              </button>
              <button onClick={handleChat} style={chatBtnStyle}>Log</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const panelStyle = {
  background: 'white',
  borderRadius: '12px',
  padding: '24px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
};
const panelTitle = {
  fontSize: '18px',
  fontWeight: '600',
  color: '#1f2937',
  marginBottom: '20px',
  paddingBottom: '12px',
  borderBottom: '1px solid #e5e7eb',
};
const fieldStyle = { marginBottom: '16px' };
const labelStyle = { display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' };
const inputStyle = { width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: '8px', fontSize: '13px', fontFamily: 'Inter, sans-serif', outline: 'none', boxSizing: 'border-box' };
const textareaStyle = { ...inputStyle, height: '72px', resize: 'none' };
const voiceBtnStyle = { display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '12px', fontFamily: 'Inter, sans-serif', marginBottom: '6px' };
const submitBtnStyle = { width: '100%', padding: '13px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: '600', cursor: 'pointer', fontFamily: 'Inter, sans-serif' };
const hintStyle = { background: '#f9fafb', borderRadius: '8px', padding: '12px', fontSize: '13px', color: '#6b7280', lineHeight: '1.6', border: '1px solid #e5e7eb' };
const chatBtnStyle = { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 16px', fontSize: '13px', cursor: 'pointer', fontWeight: '600', whiteSpace: 'nowrap' };
const successBanner = { background: '#d1fae5', color: '#065f46', padding: '12px', textAlign: 'center', fontSize: '14px', fontWeight: '500' };

export default LogInteraction;