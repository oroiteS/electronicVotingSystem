<template>
  <div class="register-page-wrapper">
    <el-row justify="center" align="middle" class="register-row">
      <el-col :xs="22" :sm="18" :md="14" :lg="12" :xl="10">
        <el-card class="register-panel" shadow="hover">
          <el-row>
            <!-- 左侧插画区域 (与登录页类似) -->
            <el-col :span="10" class="panel-left hidden-xs-only">
              <div class="illustration-container">
                 <div class="decorative-graphics">
                    <div class="circle circle-1" style="background-color: rgba(255,255,255,0.2);"></div>
                    <div class="circle circle-2" style="background-color: rgba(255,255,255,0.25);"></div>
                    <div class="bar bar-1" style="transform: rotate(45deg) translateX(35px);"></div>
                    <div class="bar bar-2" style="transform: rotate(-30deg) translateX(-25px) translateY(15px);"></div>
                    <div class="bar bar-3" style="transform: rotate(80deg) translateY(-40px);"></div>
                    <el-icon class="icon-decor icon-1"><EditPen /></el-icon>
                    <el-icon class="icon-decor icon-2"><CircleCheck /></el-icon>
                 </div>
                <p class="illustration-text">创建您的投票账户</p>
              </div>
            </el-col>

            <!-- 右侧注册表单区域 -->
            <el-col :xs="24" :sm="14" class="panel-right">
              <div class="register-form-container">
                <h2 class="form-title">用户注册</h2>
                <p class="form-subtitle">加入我们，参与投票！</p>
                <el-form
                  ref="registerFormRef"
                  :model="registerForm"
                  :rules="registerRules"
                  label-position="top"
                >
                  <el-form-item label="用户ID" prop="userid">
                    <el-input
                      v-model="registerForm.userid"
                      placeholder="请输入用户ID (例如：学号、工号)"
                      size="large"
                      :prefix-icon="UserIcon"
                    />
                  </el-form-item>
                  <el-form-item label="密码" prop="password">
                    <el-input
                      type="password"
                      v-model="registerForm.password"
                      placeholder="请输入密码 (至少6位)"
                      show-password
                      size="large"
                      :prefix-icon="LockIcon"
                    />
                  </el-form-item>
                  <el-form-item label="确认密码" prop="confirmPassword">
                    <el-input
                      type="password"
                      v-model="registerForm.confirmPassword"
                      placeholder="请再次输入密码"
                      show-password
                      size="large"
                      :prefix-icon="LockIcon"
                    />
                  </el-form-item>
                  <el-form-item label="以太坊地址" prop="ethereum_address">
                    <el-select 
                      v-model="registerForm.ethereum_address" 
                      placeholder="选择一个可用的以太坊地址" 
                      style="width: 100%;" 
                      size="large"
                      filterable
                      :loading="fetchingAddresses"
                    >
                      <template #prefix><WalletIcon style="margin-top: 7px;"/></template>
                      <el-option
                        v-for="address in availableAddresses"
                        :key="address"
                        :label="address"
                        :value="address"
                      />
                    </el-select>
                    <el-button @click="fetchAddresses" :loading="fetchingAddresses" size="small" text type="primary" style="margin-left: 5px; margin-top: 5px;">
                        <el-icon><Refresh /></el-icon>刷新列表
                    </el-button>
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      @click="handleRegister"
                      :loading="loading"
                      class="register-button"
                      size="large"
                    >
                      注 册
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="extra-links">
                  <el-link type="primary" @click="goToLogin">已有账户？直接登录</el-link>
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
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import apiService from '@/services/api';
import { ElMessage } from 'element-plus';
import { User as UserIcon, Lock as LockIcon, Wallet as WalletIcon, EditPen, CircleCheck, Refresh } from '@element-plus/icons-vue'; // 引入图标

const router = useRouter();
const authStore = useAuthStore();

const registerFormRef = ref(null);
const registerForm = ref({
  userid: '',
  password: '',
  confirmPassword: '',
  ethereum_address: ''
});
const loading = ref(false);
const fetchingAddresses = ref(false);
const availableAddresses = ref([]);

const authError = computed(() => authStore.error);

const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'));
  } else if (value !== registerForm.value.password) {
    callback(new Error('两次输入的密码不一致!'));
  } else {
    callback();
  }
};

const registerRules = {
  userid: [{ required: true, message: '请输入用户ID', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ],
  ethereum_address: [{ required: true, message: '请选择一个以太坊地址', trigger: 'change' }]
};

const fetchAddresses = async () => {
  fetchingAddresses.value = true;
  authStore.error = null; // 清除旧错误
  try {
    const response = await apiService.getAvailableEthAddresses();
    if (response.data.success) {
      availableAddresses.value = response.data.available_addresses;
      if (availableAddresses.value.length === 0) {
        ElMessage.warning('当前没有可用的以太坊地址供注册。');
      }
    } else {
      ElMessage.error(response.data.message || '获取可用地址失败');
    }
  } catch (error) {
    const errMsg = error.response?.data?.message || error.message || '获取可用地址时出错';
    ElMessage.error(errMsg);
    console.error("Fetch address error:", errMsg);
  } finally {
    fetchingAddresses.value = false;
  }
};

onMounted(fetchAddresses);

const handleRegister = async () => {
  if (!registerFormRef.value) return;
  registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      authStore.error = null; // 清除旧错误
      const success = await authStore.register({
        userid: registerForm.value.userid,
        password: registerForm.value.password,
        ethereum_address: registerForm.value.ethereum_address
      });
      loading.value = false;
      if (success) {
        ElMessage.success('注册成功！请登录。');
        router.push('/login');
      } else {
        // authStore.error 会被 computed 属性捕获显示
      }
    } else {
      ElMessage.error('请完整填写表单并修正错误');
      return false;
    }
  });
};

const goToLogin = () => {
  router.push('/login');
};
</script>

<style scoped>
/* 大部分样式与登录页共享，可以考虑提取到全局或公共样式文件 */
.register-page-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #6E54EF 0%, #409EFF 100%); /* 与登录页相反的渐变方向 */
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  box-sizing: border-box;
}

.register-row {
  width: 100%;
}

.register-panel {
  border-radius: 12px;
  overflow: hidden;
}

.panel-left {
  background-color: #6a5acd;
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

.decorative-graphics {
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

.register-form-container {
  max-width: 400px; /* 注册表单可以略宽 */
  margin: 0 auto;
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

.register-form-container .el-form-item__label {
  font-size: 15px;
  color: #606266;
  margin-bottom: 2px !important;
}

.register-form-container .el-input--large .el-input__inner,
.register-form-container .el-select--large .el-select-v2__wrapper .el-select-v2__placeholder,
.register-form-container .el-select--large .el-input__inner {
  font-size: 16px;
}
.register-form-container .el-select-dropdown__item {
    font-size: 15px;
}
.register-form-container .el-input--large .el-input__prefix .el-input__icon,
.register-form-container .el-input--large .el-input__suffix .el-input__icon,
.register-form-container .el-select--large .el-input__prefix .el-input__icon {
    font-size: 16px;
}


.register-button {
  width: 100%;
}

.extra-links {
  margin-top: 20px;
  text-align: center;
}
.extra-links .el-link {
    font-size: 14px;
}

.page-footer {
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 30px;
  font-size: 14px;
}

@media (max-width: 768px) {
  .panel-left {
    display: none;
  }
  .panel-right {
    border-radius: 12px;
     padding: 30px 20px;
  }
   .register-panel .el-row > .el-col {
    padding-left: 0 !important;
    padding-right: 0 !important;
  }
  .form-title {
    font-size: 22px;
  }
  .register-form-container .el-form-item__label {
    font-size: 14px;
  }
  .register-form-container .el-input--large .el-input__inner,
  .register-form-container .el-select--large .el-select-v2__wrapper .el-select-v2__placeholder,
  .register-form-container .el-select--large .el-input__inner {
    font-size: 15px;
  }
   .register-form-container .el-select-dropdown__item {
    font-size: 14px;
  }
  .register-form-container .el-button--large {
    font-size: 15px;
  }
}
</style>