import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import API from '../../api/axios';

export const fetchInteractions = createAsyncThunk('interactions/fetchAll', async () => {
  const res = await API.get('/api/interactions');
  return res.data;
});

export const createInteraction = createAsyncThunk('interactions/create', async (data) => {
  const res = await API.post('/api/interactions', data);
  return res.data;
});

export const updateInteraction = createAsyncThunk('interactions/update', async ({ id, data }) => {
  const res = await API.put(`/api/interactions/${id}`, data);
  return res.data;
});

export const deleteInteraction = createAsyncThunk('interactions/delete', async (id) => {
  await API.delete(`/api/interactions/${id}`);
  return id;
});

export const sendChat = createAsyncThunk('interactions/chat', async (message) => {
  const res = await API.post('/api/chat', { message });
  return res.data;
});

const interactionSlice = createSlice({
  name: 'interactions',
  initialState: {
    list: [],
    loading: false,
    error: null,
    chatResponse: null,
    stats: null,
  },
  reducers: {
    clearChatResponse: (state) => {
      state.chatResponse = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => { state.loading = true; })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state) => { state.loading = false; })
      .addCase(createInteraction.fulfilled, (state, action) => {
        state.list.unshift(action.payload);
      })
      .addCase(updateInteraction.fulfilled, (state, action) => {
        const index = state.list.findIndex(i => i.id === action.payload.id);
        if (index !== -1) state.list[index] = action.payload;
      })
      .addCase(deleteInteraction.fulfilled, (state, action) => {
        state.list = state.list.filter(i => i.id !== action.payload);
      })
      .addCase(sendChat.pending, (state) => { state.loading = true; })
      .addCase(sendChat.fulfilled, (state, action) => {
        state.loading = false;
        state.chatResponse = action.payload;
      })
      .addCase(sendChat.rejected, (state) => { state.loading = false; });
  },
});

export const { clearChatResponse } = interactionSlice.actions;
export default interactionSlice.reducer;