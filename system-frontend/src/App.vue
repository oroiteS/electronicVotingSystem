<template>
  <div id="app-layout">
    <el-header v-if="authStore.isAuthenticated" class="app-header">
      <div class="logo">投票系统</div>
      <div class="user-actions">
        <span v-if="authStore.user" style="margin-right: 15px;">你好, {{ authStore.user.userid }}</span>
        <el-button type="info" plain @click="authStore.logout()">登出</el-button>
      </div>
    </el-header>
    <el-main :class="{ 'content-with-header': authStore.isAuthenticated, 'content-no-header': !authStore.isAuthenticated }">
      <router-view />
    </el-main>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/store/auth';
// import { onMounted } from 'vue';

const authStore = useAuthStore();

// 可选：如果希望在应用加载时自动尝试获取用户信息（如果token存在）
// onMounted(() => {
//   if (authStore.isAuthenticated && !authStore.user) {
//     authStore.fetchCurrentUserProfile();
//   }
// });
</script>

<style>
/* 全局样式或重置，根据需要添加 */
body, html {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

#app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #409EFF;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px; /* Element Plus header 默认高度 */
  line-height: 60px;
}
.logo {
  font-size: 20px;
  font-weight: bold;
}

.content-with-header {
  /* padding-top: 60px;  如果 header 是 fixed 定位，main 才需要 padding-top */
  flex-grow: 1; /* 让 main 内容区域占据剩余空间 */
}
.content-no-header {
   flex-grow: 1;
}
</style>
