// src/store/auth.js
import { defineStore } from 'pinia';
import apiService from '@/services/api'; // 假设 api.js 在 services 目录下
import router from '@/router'; // 导入 router 实例用于导航

export const useAuthStore = defineStore('auth', {
    state: () => ({
        accessToken: localStorage.getItem('accessToken') || null,
        user: JSON.parse(localStorage.getItem('user')) || null, // 存储用户信息
        status: '', // 'loading', 'success', 'error'
        error: null,
    }),
    getters: {
        isAuthenticated: (state) => !!state.accessToken,
        isAdmin: (state) => state.user && state.user.role === 'admin',
        currentUser: (state) => state.user,
    },
    actions: {
        async login(credentials) {
            this.status = 'loading';
            this.error = null;
            try {
                const response = await apiService.login(credentials);
                if (response.data.success) {
                    const token = response.data.access_token;
                    const userData = response.data.user;

                    this.accessToken = token;
                    this.user = userData;
                    localStorage.setItem('accessToken', token);
                    localStorage.setItem('user', JSON.stringify(userData));
                    this.status = 'success';
                    // 登录成功后，可以根据用户角色导航到不同页面
                    router.push('/'); // 到首页
                    return true;
                } else {
                    throw new Error(response.data.message || 'Login failed');
                }
            } catch (error) {
                this.status = 'error';
                const errorMessage = error.response?.data?.message || error.message || 'An unknown error occurred during login.';
                this.error = errorMessage;
                localStorage.removeItem('accessToken');
                localStorage.removeItem('user');
                console.error('Login error:', errorMessage);
                return false;
            }
        },
        async register(userData) {
            this.status = 'loading';
            this.error = null;
            try {
                const response = await apiService.register(userData);
                if (response.data.success) {
                    this.status = 'success';
                    // 注册成功后，可以提示用户登录或自动登录
                    // router.push('/login');
                    return true;
                } else {
                    throw new Error(response.data.message || 'Registration failed');
                }
            } catch (error) {
                this.status = 'error';
                const errorMessage = error.response?.data?.message || error.message || 'An unknown error occurred during registration.';
                this.error = errorMessage;
                console.error('Registration error:', errorMessage);
                return false;
            }
        },
        logout() {
            this.accessToken = null;
            this.user = null;
            localStorage.removeItem('accessToken');
            localStorage.removeItem('user');
            this.status = '';
            router.push('/login');
        },
        // 可选: Action 来获取当前用户信息 (例如在应用加载时)
        async fetchCurrentUserProfile() {
            if (!this.accessToken) return; // 如果没有 token，不尝试获取
            this.status = 'loading';
            try {
                const response = await apiService.getCurrentUserProfile();
                if (response.data.success) {
                    this.user = response.data.user;
                    localStorage.setItem('user', JSON.stringify(response.data.user)); // 更新本地存储的用户信息
                    this.status = 'success';
                } else {
                    // Token 可能有效，但用户在后端找不到了，或者其他问题
                    this.logout(); // 安全起见，登出
                }
            } catch (error) {
                console.error("Error fetching user profile:", error);
                if (error.response && error.response.status === 401) {
                    this.logout(); // Token 无效，登出
                } else {
                    this.status = 'error';
                    this.error = "Could not fetch user profile.";
                }
            }
        }
    },
});