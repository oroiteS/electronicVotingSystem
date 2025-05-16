import axios from 'axios';
import router from '@/router'; // 导入 router 以便在拦截器中使用

// 从环境变量获取 API 基础 URL，或者硬编码 (不推荐用于生产)
const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://127.0.0.1:5000/api';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

// 请求拦截器：在每个请求发送前附加 JWT (如果存在)
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('accessToken'); // 从 localStorage 获取 token
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 响应拦截器：可以用于全局错误处理或 token 刷新逻辑
apiClient.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        if (error.response && error.response.status === 401) {
            console.error("API Error: Unauthorized (401). Token might be invalid or expired.");
            // 清理本地存储
            localStorage.removeItem('accessToken');
            localStorage.removeItem('user');
            
            // 触发 Pinia store 中的 logout action（如果 store 已初始化且可访问）
            // 注意：直接在这里导入和使用 store 可能导致循环依赖或 store 未初始化的问题
            // 更稳健的做法是通过事件总线，或者让调用方处理401后的登出逻辑
            // 此处为了简单，直接导航，但 Pinia store 中的 logout 应该包含清理逻辑
            
            // 检查当前是否已在登录页，避免无限重定向
            if (router.currentRoute.value.name !== 'Login') {
                 router.push({ name: 'Login' }).catch(err => {
                    if (err.name !== 'NavigationDuplicated') { // 忽略重复导航错误
                        console.error('Router push error after 401:', err);
                    }
                });
            }
        }
        return Promise.reject(error);
    }
);


export default {
    // --- Auth Service ---
    login(credentials) { // credentials: { userid, password }
        return apiClient.post('/auth/login', credentials);
    },
    register(userData) { // userData: { userid, password, ethereum_address }
        return apiClient.post('/auth/register', userData);
    },
    getAvailableEthAddresses() {
        return apiClient.get('/auth/available_eth_addresses');
    },
    getCurrentUserProfile() {
        return apiClient.get('/auth/me');
    },

    // --- User Service ---
    applyForVoter(applicationData) { // applicationData: { application_text } (user_id 从 token 获取)
        return apiClient.post('/user/apply_voter', applicationData);
    },

    // --- Admin Service ---
    // 对于管理员接口，token 会由请求拦截器自动添加
    addCandidate(candidateData) { // { name, description, slogan }
        return apiClient.post('/admin/add_candidate', candidateData);
    },
    getVoterApplications(status = 'pending', page = 1, perPage = 10) {
        return apiClient.get(`/admin/voter_applications?status=${status}&page=${page}&per_page=${perPage}`);
    },
    reviewVoterApplication(applicationId, reviewData) { // reviewData: { status, admin_notes }
        return apiClient.put(`/admin/voter_applications/${applicationId}/review`, reviewData);
    },

    // --- New Admin Voting Activity Management ---
    setVotingPeriod(periodData) { // periodData: { start_time_timestamp: number, end_time_timestamp: number }
        return apiClient.post('/admin/voting/period', periodData);
    },
    startVoting() {
        return apiClient.post('/admin/voting/start');
    },
    endVoting() {
        return apiClient.post('/admin/voting/end');
    },
    extendVotingDeadline(deadlineData) { // deadlineData: { new_end_time_timestamp: number }
        return apiClient.put('/admin/voting/extend', deadlineData);
    },
    getContractVotingStatus() { // For admin panel to get detailed status
        return apiClient.get('/admin/voting/contract_status');
    },

    // --- Vote Service (Public and Protected) ---
    // 公开接口
    getAllCandidates() {
        return apiClient.get('/candidates');
    },
    getVotingStatus() {
        return apiClient.get('/voting_status');
    },
    getElectionDeadline() {
        return apiClient.get('/election_deadline');
    },
    // 受保护接口 (token 由拦截器添加)
    castVote(voteData) { // voteData: { candidate_index_on_chain }
        return apiClient.post('/vote', voteData);
    },
    revokeVote() { // 撤销投票通常不需要请求体，token 会包含用户信息
        return apiClient.post('/revoke_vote');
    },
    uploadCandidateImage(formData) {
        return apiClient.post('/admin/upload_candidate_image', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
    },
};
