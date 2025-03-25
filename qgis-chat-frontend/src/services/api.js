import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
});

export const sendCommand = async (prompt) => {
  try {
    const response = await api.post('/', { prompt });
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    return { status: 'error', message: error.message };
  }
};
