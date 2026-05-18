// src/apis/api.js
import axios from 'axios';

class BaseApi {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
    console.log('API Base URL:', this.baseURL);

    this.axiosInstance = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
}

export { BaseApi };