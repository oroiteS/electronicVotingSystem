<template>
  <div class="login-page-wrapper">
    <el-row justify="center" align="middle" class="login-row">
      <el-col :xs="22" :sm="16" :md="12" :lg="10" :xl="8">
        <el-card class="login-panel" shadow="hover">
          <el-row>
            <!-- 左侧插画区域 -->
            <el-col :span="10" class="panel-left hidden-xs-only">
              <div class="illustration-container">
                <img src="@/assets/logo.png" alt="Voting System Illustration" class="illustration-img" v-if="true"> 
                <p class="illustration-text">区块链电子投票系统</p>
              </div>
            </el-col>

            <!-- 右侧登录表单区域 -->
            <el-col :xs="24" :sm="14" class="panel-right" css="font-size:25px">
              <div class="login-form-container">
                <h2 class="form-title">用户登录</h2>
                <p class="form-subtitle">欢迎回来！</p>
                <el-form
                  ref="loginFormRef"
                  :model="loginForm"
                  :rules="loginRules"
                  label-position="top"
                  @keyup.enter="handleLogin"
                >
                  <el-form-item label="用户ID" prop="userid">
                    <el-input
                      v-model="loginForm.userid"
                      placeholder="请输入用户ID"
                      size="large"
                      :prefix-icon="UserIcon"
                    />
                  </el-form-item>
                  <el-form-item label="密码" prop="password">
                    <el-input
                      type="password"
                      v-model="loginForm.password"
                      placeholder="请输入密码"
                      show-password
                      size="large"
                      :prefix-icon="LockIcon"
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      @click="handleLogin"
                      :loading="loading"
                      class="login-button"
                      size="large"
                    >
                      登 录
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="extra-links">
                  <el-link type="primary" @click="goToRegister">没有账户？立即注册</el-link>
                </div>
                <el-alert v-if="authError" :title="authError" type="error" show-icon :closable="false" style="margin-top: 15px;" />
              </div>
            </el-col>
          </el-row>
        </el-card>
        <footer class="page-footer">
          Copyright 2024 © 电子投票系统
        </footer>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { ElMessage } from 'element-plus';
import { User as UserIcon, Lock as LockIcon} from '@element-plus/icons-vue'; // 引入图标

const router = useRouter();
const authStore = useAuthStore();

const loginFormRef = ref(null);
const loginForm = ref({
  userid: '',
  password: ''
});
const loading = ref(false);

const authError = computed(() => authStore.error);

const loginRules = {
  userid: [{ required: true, message: '请输入用户ID', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
};

const handleLogin = async () => {
  if (!loginFormRef.value) return;
  loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      authStore.error = null; // 清除之前的错误
      const success = await authStore.login(loginForm.value);
      loading.value = false;
      if (success) {
        ElMessage.success('登录成功!');
        // 导航已在 store action 中处理
      } else {
        // authStore.error 会被 computed 属性捕获显示
      }
    } else {
      ElMessage.error('请完整填写表单');
      return false;
    }
  });
};

const goToRegister = () => {
  router.push('/register');
};
</script>

<style scoped>
.login-page-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #409EFF 0%, #6E54EF 100%); /* 漂亮的渐变背景 */
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  box-sizing: border-box;
}

.login-row {
  width: 100%;
}

.login-panel {
  border-radius: 12px;
  overflow: hidden; /* 确保内部元素不会溢出圆角 */
}

.panel-left {
  background-color: #5a8dee; /* 左侧背景色，可以调整或使用图片 */
  padding: 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: white;
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
}

.illustration-container {
  text-align: center;
}

.decorative-graphics { /* 简单的CSS图形替代插画 */
  width: 180px;
  height: 180px;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  position: relative;
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.circle {
  position: absolute;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.15);
}
.circle-1 { width: 120px; height: 120px; opacity: 0.8; }
.circle-2 { width: 80px; height: 80px; opacity: 0.6; }
.bar {
  position: absolute;
  background-color: #fff;
  border-radius: 3px;
}
.bar-1 { width: 10px; height: 50px; transform: rotate(30deg) translateX(30px); }
.bar-2 { width: 8px; height: 70px; transform: rotate(-45deg) translateX(-20px) translateY(10px); }
.bar-3 { width: 12px; height: 40px; transform: rotate(70deg) translateY(-35px); }

.icon-decor {
  font-size: 30px;
  color: rgba(255,255,255,0.7);
  position: absolute;
}
.icon-1 { top: 30px; left: 40px;}
.icon-2 { bottom: 30px; right: 40px;}


.illustration-img {
  max-width: 80%;
  height: auto;
  margin-bottom: 20px;
}

.illustration-text {
  font-size: 1.5em;
  font-weight: bold;
}

.panel-right {
  padding: 40px 30px;
  background-color: #fff;
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
}

.login-form-container {
  max-width: 350px; /* 限制表单最大宽度 */
  margin: 0 auto; /* 水平居中 */
}

.form-title {
  text-align: center;
  font-size: 26px; /* 略微增大标题字体 */
  font-weight: 500;
  color: #303133;
  margin-bottom: 10px;
}

.form-subtitle {
  text-align: center;
  color: #909399;
  margin-bottom: 30px;
  font-size: 15px; /* 略微增大副标题字体 */
}

/* --- 字体增大关键修改 --- */
.login-form-container .el-form-item__label {
  font-size: 15px; /* 增大标签字体 */
  color: #606266; /* 可以调整标签颜色使其更清晰 */
  margin-bottom: 2px !important; /* 调整标签和输入框间距 */
}

.login-form-container .el-input--large .el-input__inner {
  font-size: 16px; /* 增大输入框内文字体 */
  /* Element Plus的 large size 输入框本身较高，如果需要调整高度可以修改 padding */
}
.login-form-container .el-input--large .el-input__prefix .el-input__icon,
.login-form-container .el-input--large .el-input__suffix .el-input__icon {
    font-size: 16px; /* 确保图标大小与文字协调 */
}


.login-form-container .el-button--large {
  font-size: 16px; /* 增大按钮文字体 */
  font-weight: 500;
}
/* --- 字体增大关键修改结束 --- */


.login-button {
  width: 100%;
}

.extra-links {
  margin-top: 20px;
  text-align: center;
}
.extra-links .el-link {
    font-size: 14px; /* 调整链接字体大小 */
}

.page-footer {
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 30px;
  font-size: 14px;
}

/* 响应式：在小屏幕上隐藏左侧插画 */
@media (max-width: 768px) { /* Element Plus的sm断点通常是768px */
  .panel-left {
    display: none;
  }
  .panel-right {
    border-radius: 12px; /* 小屏幕时右侧面板也应用圆角 */
    padding: 30px 20px;
  }
  .login-panel .el-row > .el-col { /* 移除小屏幕下col的padding（如果有）*/
    padding-left: 0 !important;
    padding-right: 0 !important;
  }
  .form-title {
    font-size: 22px; /* 小屏幕上标题可以小一点 */
  }
  .login-form-container .el-form-item__label {
    font-size: 14px;
  }
  .login-form-container .el-input--large .el-input__inner {
    font-size: 15px;
  }
  .login-form-container .el-button--large {
    font-size: 15px;
  }
}
</style>