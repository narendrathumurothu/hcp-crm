import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import interactionReducer from './slices/interactionSlice';

const store = configureStore({
  reducer: {
    auth: authReducer,
    interactions: interactionReducer,
  },
});

export default store;