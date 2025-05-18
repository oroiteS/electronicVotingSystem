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
            <p>当前投票阶段: 
              <el-tag :type="votingStatusInfo.phase === 'Active' ? 'success' : (votingStatusInfo.phase === 'Pending' ? 'info' : (votingStatusInfo.phase === 'Concluded' ? 'warning' : 'danger'))">
                {{ votingStatusInfo.phase || '未知' }}
              </el-tag>
            </p>
            <p>投票是否已开始: <el-tag :type="votingStatusInfo.isStarted ? 'success' : 'info'">{{ votingStatusInfo.isStarted ? '是' : '否' }}</el-tag></p>
            <p>投票是否已结束: <el-tag :type="votingStatusInfo.isEnded ? 'success' : 'info'">{{ votingStatusInfo.isEnded ? '是' : '否' }}</el-tag></p>
            <p>预设开始时间: {{ formatDateTime(votingStatusInfo.startTime) }}</p>
            <p>预设结束时间: {{ formatDateTime(votingStatusInfo.endTime) }}</p>
            
            <!-- 新增：显示候选人得票信息 -->
            <div v-if="votingStatusInfo.isStarted" style="margin-top: 15px;">
              <el-divider content-position="left">候选人得票情况</el-divider>
              <div v-if="candidatesWithVotes.length > 0">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item 
                    v-for="candidate in candidatesWithVotes" 
                    :key="candidate.id_on_chain" 
                    :label="candidate.name">
                    <el-tag type="info" effect="plain" round>
                      {{ candidate.vote_count_from_chain }} 票
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </div>
              <p v-else>
                投票已开始/结束，当前暂无候选人得票数据或正在加载...
              </p>
            </div>

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
const votingStatusInfo = ref(null);
const showApplyDialog = ref(false);
const candidatesWithVotes = ref([]); // 新增: 存储候选人及其票数

const isRegisteredVoter = computed(() => {
  return currentUser.value &&
    currentUser.value.is_voter &&
    currentUser.value.voter_is_registered_on_chain;
});

const canApplyForVoter = computed(() => {
  if (!currentUser.value || currentUser.value.role === 'admin') return false;
  return !currentUser.value.voter_application_status || currentUser.value.voter_application_status === 'rejected';
});

const canVote = computed(() => {
  return isRegisteredVoter.value &&
    votingStatusInfo.value &&
    votingStatusInfo.value.isStarted &&
    !votingStatusInfo.value.isEnded;
});


const fetchCurrentUser = async () => {
  const loadingInstance = ElLoading.service({ text: '加载用户信息...' });
  try {
    const response = await api.getCurrentUserProfile();
    if (response.data.success) {
      currentUser.value = response.data.user;
      console.log('Current user data:', currentUser.value);
    } else {
      ElMessage.error(response.data.message || '获取用户信息失败');
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

const fetchCandidatesWithVotes = async () => {
  const loadingInstance = ElLoading.service({ text: '加载候选人得票信息...' });
  try {
    const response = await api.getAllCandidates(); // API 调用获取候选人列表及票数
    if (response.data.success && response.data.candidates) {
      candidatesWithVotes.value = response.data.candidates;
      console.log('Candidates with votes:', candidatesWithVotes.value);
    } else {
      ElMessage.warning(response.data.message || '获取候选人得票信息失败。');
      candidatesWithVotes.value = [];
    }
  } catch (error) {
    console.error('Error fetching candidates with votes:', error);
    ElMessage.error('获取候选人得票信息时发生错误。');
    candidatesWithVotes.value = [];
  } finally {
    loadingInstance.close();
  }
};

const fetchVotingStatus = async () => {
  const loadingInstance = ElLoading.service({ text: '加载投票状态...' });
  try {
    const response = await api.getVotingStatus();
    if (response.data.success) {
      votingStatusInfo.value = response.data;
      console.log('Voting status:', votingStatusInfo.value);

      if (votingStatusInfo.value.isStarted) { // 如果投票已开始或已结束
        await fetchCandidatesWithVotes();
      } else {
        candidatesWithVotes.value = []; // 投票未开始则清空
      }
    } else {
      ElMessage.warning(response.data.message || '获取投票状态失败，将使用默认值。');
      votingStatusInfo.value = { phase: "Error", phase_code: -1, isStarted: false, isEnded: true, startTime: 0, endTime: 0 };
      candidatesWithVotes.value = []; // 获取状态失败也清空
    }
  } catch (error) {
    console.error('Error fetching voting status:', error);
    ElMessage.error('获取投票状态时发生错误。');
    votingStatusInfo.value = { phase: "Error", phase_code: -1, isStarted: false, isEnded: true, startTime: 0, endTime: 0 };
    candidatesWithVotes.value = []; // 发生错误也清空
  } finally {
    loadingInstance.close();
  }
};

const submitVoterApplication = async () => {
  const loadingInstance = ElLoading.service({ text: '正在提交申请...' });
  try {
    const response = await api.applyForVoter({});
    if (response.data.success) {
      ElMessage.success('选民申请已成功提交！');
      showApplyDialog.value = false;
      await fetchCurrentUser();
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

const formatDateTime = (timestampInSeconds) => {
  if (!timestampInSeconds || timestampInSeconds === 0) return '未设置';
  try {
    // 时间戳是秒，Date构造函数需要毫秒
    return new Date(timestampInSeconds * 1000).toLocaleString();
  } catch (e) {
    console.error('Error formatting date:', e);
    return '日期格式无效';
  }
};

const goToVotePage = () => {
  router.push('/vote');
};

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