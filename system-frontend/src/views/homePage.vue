<template>
  <el-container style="padding: 20px;">
    <el-main>
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>欢迎回来！</span>
          </div>
        </template>

        <!-- 用户基本信息 -->
        <div v-if="currentUser">
          <el-descriptions title="您的信息" :column="2" border>
            <el-descriptions-item label="用户ID">{{ currentUser.userid }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag :type="currentUser.role === 'admin' ? 'success' : 'primary'">
                {{ currentUser.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="以太坊地址">
              {{ currentUser.ethereum_address || '未设置' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <el-empty v-else description="正在加载用户信息..."></el-empty>

        <!-- 全局投票状态 -->
        <el-card shadow="never" style="margin-top: 20px;">
          <template #header>
            <span>投票状态</span>
          </template>
          <div v-if="votingStatusInfo">
            <p>投票是否已开始: <el-tag :type="votingStatusInfo.isStarted ? 'success' : 'info'">{{ votingStatusInfo.isStarted ?
                '是' :
                '否' }}</el-tag></p>
            <p>投票是否已结束: <el-tag :type="votingStatusInfo.isEnded ? 'success' : 'info'">{{ votingStatusInfo.isEnded ? '是'
                : '否'
                }}</el-tag></p>
            <p v-if="votingStatusInfo.votingDeadlineTimestamp">截止时间: {{
              formatDateTime(votingStatusInfo.votingDeadlineTimestamp)
              }}</p>
          </div>
          <el-empty v-else description="正在加载投票状态..."></el-empty>
        </el-card>

        <!-- 管理员仪表盘 -->
        <AdminDashboard v-if="currentUser && currentUser.role === 'admin'" />

        <!-- 普通用户操作区 -->
        <el-card shadow="never" style="margin-top: 20px;" v-if="currentUser && currentUser.role === 'user'">
          <template #header>
            <span>您的投票状态与操作</span>
          </template>
          <div>
            <!-- 申请成为选民 -->
            <div v-if="canApplyForVoter">
              <p>您还不是注册选民，或者您的上一次申请已被拒绝。</p>
              <el-button type="primary" @click="showApplyDialog = true">申请成为选民</el-button>
            </div>
            <div v-else-if="currentUser.voter_application_status === 'pending'">
              <p>您的选民申请 (ID: {{ currentUser.voter_application_id }}) 正在审核中，请耐心等待。</p>
            </div>
            <div v-else-if="currentUser.voter_application_status === 'approved' && !currentUser.is_voter">
              <p>您的选民申请 (ID: {{ currentUser.voter_application_id }}) 已被批准！请等待管理员为您分配以太坊地址并完成链上注册。</p>
            </div>
            <div
              v-else-if="currentUser.voter_application_status === 'approved' && currentUser.is_voter && !currentUser.voter_is_registered_on_chain">
              <p>您的选民资格已确认，以太坊地址为: {{ currentUser.ethereum_address }}。请等待管理员完成链上注册。</p>
            </div>

            <!-- 已是注册选民 -->
            <div v-if="isRegisteredVoter">
              <p>您已是注册选民。以太坊地址: {{ currentUser.ethereum_address }}</p>
              <div v-if="votingStatusInfo">
                <div v-if="canVote">
                  <el-button type="success" @click="goToVotePage">进入投票页面</el-button>
                </div>
                <p v-else-if="!votingStatusInfo.isStarted">投票尚未开始。</p>
                <p v-else-if="votingStatusInfo.isEnded">投票已结束。</p>
              </div>
            </div>
            <el-empty
              v-if="!canApplyForVoter && currentUser.voter_application_status !== 'pending' && !isRegisteredVoter && !(currentUser.voter_application_status === 'approved')"
              description="暂无更多操作。"></el-empty>
          </div>
        </el-card>


      </el-card>

      <!-- 申请成为选民对话框 -->
      <el-dialog v-model="showApplyDialog" title="申请成为选民" width="30%">
        <p>您确定要提交选民资格申请吗？</p>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showApplyDialog = false">取消</el-button>
            <el-button type="primary" @click="submitVoterApplication">确认提交</el-button>
          </span>
        </template>
      </el-dialog>

    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api'; // 确保路径正确
import { ElMessage, ElLoading } from 'element-plus';
import AdminDashboard from '@/components/adminDashboard.vue';

const router = useRouter();
const currentUser = ref(null);
const votingStatusInfo = ref(null); // { voting_has_started: bool, voting_has_ended: bool, start_time: string, end_time: string }
const showApplyDialog = ref(false);

// --- Computed Properties ---
const isRegisteredVoter = computed(() => {
  return currentUser.value &&
    currentUser.value.is_voter && // 在 voters 表中有记录
    currentUser.value.voter_is_registered_on_chain; // 并且已在链上注册
});

const canApplyForVoter = computed(() => {
  if (!currentUser.value || currentUser.value.role === 'admin') return false;
  // 如果是普通用户，且没有申请，或者最近的申请是 rejected，则可以申请
  return !currentUser.value.voter_application_status || currentUser.value.voter_application_status === 'rejected';
});

const canVote = computed(() => {
  return isRegisteredVoter.value &&
    votingStatusInfo.value &&
    votingStatusInfo.value.isStarted &&
    !votingStatusInfo.value.isEnded;
});


// --- Methods ---
const fetchCurrentUser = async () => {
  const loadingInstance = ElLoading.service({ text: '加载用户信息...' });
  try {
    const response = await api.getCurrentUserProfile();
    if (response.data.success) {
      currentUser.value = response.data.user;
      console.log('Current user data:', currentUser.value);
    } else {
      ElMessage.error(response.data.message || '获取用户信息失败');
      // 可能需要重定向到登录页，如果token失效等
      // router.push('/login');
    }
  } catch (error) {
    console.error('Error fetching current user:', error);
    ElMessage.error('获取用户信息时发生错误，请检查网络或联系管理员。');
    // router.push('/login');
  } finally {
    loadingInstance.close();
  }
};

const fetchVotingStatus = async () => {
  // 假设你有一个 api.getVotingStatus() 函数
  // 这个函数应该调用后端的 `/api/vote/status` 或类似接口
  try {
    const response = await api.getVotingStatus(); // 你需要实现这个 API 调用
    if (response.data.success) {
      votingStatusInfo.value = response.data;
      console.log('Voting status:', votingStatusInfo.value.success);
      console.log('votingDeadlineTimestamp:', votingStatusInfo.value.votingDeadlineTimestamp);
    } else {
      ElMessage.warning(response.data.message || '获取投票状态失败，将使用默认值。');
      // 可以设置一个默认状态，或者让用户知道信息不完整
      votingStatusInfo.value = { voting_has_started: false, voting_has_ended: false, start_time: null, end_time: null };
    }
  } catch (error) {
    console.error('Error fetching voting status:', error);
    ElMessage.error('获取投票状态时发生错误。');
    votingStatusInfo.value = { voting_has_started: false, voting_has_ended: false, start_time: null, end_time: null };
  }
};

const submitVoterApplication = async () => {
  const loadingInstance = ElLoading.service({ text: '正在提交申请...' });
  try {
    // 假设 api.applyToBeVoter() 不需要请求体，或一个空对象
    // 根据你对 VoterApplication 模型的修改，后端接口可能不再需要具体申请内容
    const response = await api.applyForVoter({}); // 确保 api.js 中有此方法
    if (response.data.success) {
      ElMessage.success('选民申请已成功提交！');
      showApplyDialog.value = false;
      await fetchCurrentUser(); // 刷新用户信息以更新状态
    } else {
      ElMessage.error(response.data.message || '提交选民申请失败。');
    }
  } catch (error) {
    console.error('Error submitting voter application:', error);
    ElMessage.error('提交申请时发生错误。');
  } finally {
    loadingInstance.close();
  }
};

const formatDateTime = (dateTimeString) => {
  if (!dateTimeString) return 'N/A';
  try {
    return new Date(dateTimeString * 1000).toLocaleString();
  } catch (e) {
    return dateTimeString; // 如果解析失败，返回原始字符串
  }
};

// --- Navigation Methods ---
const goToVotePage = () => {
  router.push('/vote'); // 假设投票页面路由为 /vote
};

// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchCurrentUser();
  await fetchVotingStatus();
});

</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1.2em;
  /* 调整欢迎语和卡片头部的字体大小 */
}

.el-card {
  margin-bottom: 20px;
}

/* 为 el-descriptions-item 的标签和内容设置一个最小宽度，防止换行过于频繁 */
:deep(.el-descriptions__label) {
  min-width: 100px;
  font-weight: bold;
}

:deep(.el-descriptions__content) {
  min-width: 150px;
}

p {
  margin-bottom: 10px;
  line-height: 1.6;
}
</style>