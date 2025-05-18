// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '../views/loginPage.vue';
import RegisterPage from '../views/registerPage.vue';
import HomePage from '../views/homePage.vue';
import VotingPage from '../views/votingPage.vue';

// 导入你的 Pinia store (如果 router 需要访问 store 来判断认证状态)
import { useAuthStore } from '@/store/auth'; // 假设 store 在 src/store 目录

// 管理员页面组件 - 使用路由懒加载
const ManageCandidates = () => import('@/views/admin/manageCandidates.vue');
const ManageVoterApplications = () => import('@/views/admin/manageApplications.vue');
const ManageVotingActivity = () => import('@/views/admin/manageVotingActivity.vue');


const routes = [
    {
        path: '/login',
        name: 'Login',
        component: LoginPage,
        meta: { requiresGuest: true } // 标记此路由为访客路由 (已登录用户不应访问)
    },
    {
        path: '/register',
        name: 'Register',
        component: RegisterPage,
        meta: { requiresGuest: true }
    },
    {
        path: '/',
        name: 'Home',
        component: HomePage,
        meta: { requiresAuth: true } // 标记此路由需要认证
    },
    // 管理员路由
    {
        path: '/admin/candidates',
        name: 'AdminManageCandidates',
        component: ManageCandidates,
        meta: { requiresAuth: true, requiresAdmin: true } // 需要认证和管理员权限
    },
    {
        path: '/admin/applications',
        name: 'AdminManageVoterApplications',
        component: ManageVoterApplications,
        meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
        path: '/admin/voting',
        name: 'AdminManageVotingActivity',
        component: ManageVotingActivity,
        meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
        path: '/vote',
        name: 'Voting',
        component: VotingPage,
        meta: { requiresAuth: true }
    },
    // 其他路由...
    {
        path: '/:catchAll(.*)*', // 捕获所有未匹配的路由
        redirect: '/login'
    }
];

const router = createRouter({
    history: createWebHistory(process.env.BASE_URL),
    routes
});

// 全局前置守卫
router.beforeEach((to, from, next) => {
    const authStore = useAuthStore();

    const isAuthenticated = authStore.isAuthenticated;
    const isAdmin = authStore.isAdmin;

    if (to.meta.requiresAuth) {
        if (!isAuthenticated) {
            authStore.logout();
            return;
        } else if (to.meta.requiresAdmin && !isAdmin) {
            console.warn("Access Denied: Admin rights required for", to.fullPath);
            next({ name: 'Home' });
            return;
        }
    } else if (to.meta.requiresGuest && isAuthenticated) {
        next({ name: 'Home' });
        return;
    }

    next();
});

export default router;