import axios from 'axios';

export const LANGUAGE = import.meta.env.VITE_LANGUAGE || 'en';

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'https://api.example.com/api/'

const backendUrl = BACKEND_URL

export const $api = axios.create({
    baseURL: backendUrl,
    // withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    }
})

$api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    });

$api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            const event = new Event('unauthorized');

            window.dispatchEvent(event);
        }

        return Promise.reject(error);
    }
);
