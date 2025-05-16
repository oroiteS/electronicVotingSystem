// src/views/admin/ManageVotingActivity.vue
<template>
  <el-container class="manage-voting-activity-container">
    <el-header height="auto" class="page-header">
      <h2>管理投票活动</h2>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>管理员</el-breadcrumb-item>
        <el-breadcrumb-item>管理投票活动</el-breadcrumb-item>
      </el-breadcrumb>
    </el-header>

    <el-main>
      <el-card class="status-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>当前投票状态 (来自合约)</span>
            <el-button type="primary" :icon="Refresh" @click="fetchContractStatus" :loading="statusLoading">刷新状态</el-button>
          </div>
        </template>
        <div v-if="contractStatus && !statusLoading">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="当前阶段 (Phase)">
              <el-tag :type="getPhaseTagType(contractStatus.phase)">{{ contractStatus.phase }} (Code: {{contractStatus.phase_code }})</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="合约当前时间 (区块时间戳)">
              {{ formatTimestamp(contractStatus.current_block_timestamp) }} ({{ contractStatus.current_block_timestamp }})
            </el-descriptions-item>
            <el-descriptions-item label="预设开始时间">
              {{ contractStatus.start_time > 0 ? formatTimestamp(contractStatus.start_time) : '未设置' }}
              <span v-if="contractStatus.start_time > 0"> ({{ contractStatus.start_time }})</span>
            </el-descriptions-item>
            <el-descriptions-item label="预设结束时间">
              {{ contractStatus.end_time > 0 ? formatTimestamp(contractStatus.end_time) : '未设置' }}
              <span v-if="contractStatus.end_time > 0"> ({{ contractStatus.end_time }})</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <el-skeleton :rows="3" animated v-if="statusLoading" />
        <el-empty description="未能加载合约状态" v-if="!contractStatus && !statusLoading && fetchStatusError" />
      </el-card>

      <!-- 操作区域 -->
      <el-card class="actions-card" shadow="never">
        <template #header><span>操作</span></template>
        
        <!-- 设置投票周期 -->
        <div class="action-section" v-if="canSetPeriod">
          <h4>1. 设置投票周期 (仅在 'Pending' 阶段)</h4>
          <el-form :model="periodForm" ref="periodFormRef" label-width="120px" :rules="periodRules">
            <el-form-item label="开始时间" prop="startTime">
              <el-date-picker
                v-model="periodForm.startTime"
                type="datetime"
                placeholder="选择投票开始日期时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="X" 
                style="width: 100%;"
              />
            </el-form-item>
            <el-form-item label="结束时间" prop="endTime">
              <el-date-picker
                v-model="periodForm.endTime"
                type="datetime"
                placeholder="选择投票结束日期时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="X" 
                style="width: 100%;"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSetPeriod" :loading="periodLoading">确认设置周期</el-button>
            </el-form-item>
          </el-form>
        </div>
        <el-alert title="投票周期已设置或当前阶段不允许设置。" type="info" show-icon :closable="false" v-else />


        <!-- 启动投票 -->
        <div class="action-section" v-if="canStartVoting">
          <h4>2. 启动投票 (仅在 'Pending' 阶段且周期已设)</h4>
           <el-popconfirm title="确定要启动投票吗？此操作将改变合约状态。" @confirm="handleStartVoting" width="250">
                <template #reference>
                    <el-button type="success" :loading="startLoading">启动投票</el-button>
                </template>
            </el-popconfirm>
        </div>
         <el-alert 
            title="不满足启动投票的条件。" 
            type="info" 
            show-icon 
            :closable="false" 
            v-if="contractStatus && contractStatus.phase === 'Pending' && !canStartVoting"
        >
            <p v-if="!(contractStatus.end_time > 0 && contractStatus.current_block_timestamp < contractStatus.end_time)">
              请确保投票结束时间已正确设置且未过。
            </p>
            <p v-if="contractStatus.candidates_count !== undefined && contractStatus.candidates_count <= 1">
              至少需要两名候选人才能开始投票 (当前: {{ contractStatus.candidates_count }} 名)。
            </p>
            <p v-if="contractStatus.start_time > 0 && contractStatus.current_block_timestamp < contractStatus.start_time">
                投票尚未到达预设的开始时间 ({{ formatTimestamp(contractStatus.start_time) }})。合约当前时间: {{ formatTimestamp(contractStatus.current_block_timestamp) }}
            </p>
        </el-alert>


        <!-- 延长截止时间 -->
        <div class="action-section" v-if="canExtendDeadline">
          <h4>3. 延长投票截止时间 (仅在 'Active' 阶段)</h4>
          <el-form :model="extendForm" ref="extendFormRef" label-width="140px" :rules="extendRules">
            <el-form-item label="新的结束时间" prop="newEndTime">
               <el-date-picker
                v-model="extendForm.newEndTime"
                type="datetime"
                placeholder="选择新的结束日期时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="X"
                style="width: 100%;"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="warning" @click="handleExtendDeadline" :loading="extendLoading">确认延长</el-button>
            </el-form-item>
          </el-form>
        </div>
        <el-alert title="当前阶段不允许延长截止时间 (需 'Active' 阶段)。" type="info" show-icon :closable="false" v-if="contractStatus && contractStatus.phase !== 'Active' && contractStatus.phase !== 'Pending'"/>


        <!-- 结束投票 -->
        <div class="action-section" v-if="canEndVoting">
          <h4>4. 手动结束投票 (仅在 'Active' 阶段)</h4>
          <el-popconfirm title="确定要立即结束投票吗？此操作不可逆。" @confirm="handleEndVoting" width="250">
            <template #reference>
                <el-button type="danger" :loading="endLoading">立即结束投票</el-button>
            </template>
          </el-popconfirm>
        </div>
        <el-alert title="当前阶段不允许结束投票 (需 'Active' 阶段)。" type="info" show-icon :closable="false" v-if="contractStatus && contractStatus.phase !== 'Active'"/>

      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '@/services/api';
import { ElMessage} from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';

const contractStatus = ref(null);
const statusLoading = ref(false);
const fetchStatusError = ref(false);

const periodFormRef = ref(null);
const periodForm = ref({
  startTime: null, // 将存储为Unix秒级时间戳
  endTime: null,   // 将存储为Unix秒级时间戳
});
const periodLoading = ref(false);

const extendFormRef = ref(null);
const extendForm = ref({
  newEndTime: null, // 将存储为Unix秒级时间戳
});
const extendLoading = ref(false);

const startLoading = ref(false);
const endLoading = ref(false);

// --- Computed properties for enabling/disabling actions ---
const canSetPeriod = computed(() => contractStatus.value && contractStatus.value.phase === 'Pending');

const canStartVoting = computed(() => {
  if (!contractStatus.value || contractStatus.value.phase !== 'Pending') return false;

  // 直接从 contractStatus 中获取候选人数量
  const hasEnoughCandidates = contractStatus.value.candidates_count !== undefined ? contractStatus.value.candidates_count > 1 : false;
  // 如果 candidates_count 未定义（例如API还没更新或调用失败），则默认为 false，不允许启动

  return contractStatus.value.end_time > 0 &&
    contractStatus.value.current_block_timestamp < contractStatus.value.end_time &&
    hasEnoughCandidates;
});

const canExtendDeadline = computed(() => contractStatus.value && contractStatus.value.phase === 'Active');
const canEndVoting = computed(() => contractStatus.value && contractStatus.value.phase === 'Active');

// --- Validation Rules ---
const periodRules = {
  startTime: [
    { required: true, message: '请选择开始时间', trigger: 'change' },
    { 
      validator: (rule, value, callback) => {
        // value-format="X" 返回的是秒级时间戳字符串
        const selectedStartTime = Number(value);
        // 获取当前时间的秒级时间戳
        const nowInSeconds = Math.floor(Date.now() / 1000);
        // 允许一些小的误差，比如几秒钟，或者如果用户选择了非常接近现在的时间，但网络传输和区块确认需要时间
        // 为简单起见，这里直接比较
        if (selectedStartTime < nowInSeconds) {
          callback(new Error('开始时间不能早于当前浏览器时间'));
        } else {
          callback();
        }
      }, 
      trigger: 'change' 
    }
  ],
  endTime: [
    { required: true, message: '请选择结束时间', trigger: 'change' },
    { validator: (rule, value, callback) => {
        if (periodForm.value.startTime && value && Number(value) <= Number(periodForm.value.startTime)) {
          callback(new Error('结束时间必须晚于开始时间'));
        } else {
          callback();
        }
      }, trigger: 'change'
    }
  ],
};

const extendRules = {
  newEndTime: [
    { required: true, message: '请选择新的结束时间', trigger: 'change' },
    { validator: (rule, value, callback) => {
        if (contractStatus.value && contractStatus.value.end_time && value && Number(value) <= Number(contractStatus.value.end_time)) {
          callback(new Error('新的结束时间必须晚于当前预设的结束时间'));
        } else {
          callback();
        }
      }, trigger: 'change'
    }
  ]
};

// --- Methods ---
const fetchContractStatus = async () => {
  statusLoading.value = true;
  fetchStatusError.value = false;
  try {
    const response = await api.getContractVotingStatus();
    if (response.data.success) {
      contractStatus.value = response.data;
    } else {
      ElMessage.error(response.data.message || '获取合约状态失败');
      fetchStatusError.value = true;
      contractStatus.value = null;
    }
  } catch (error) {
    console.error('Error fetching contract status:', error);
    ElMessage.error('获取合约状态时发生网络错误。');
    fetchStatusError.value = true;
    contractStatus.value = null;
  } finally {
    statusLoading.value = false;
  }
};

const handleSetPeriod = async () => {
  if (!periodFormRef.value) return;
  periodFormRef.value.validate(async (valid) => {
    if (valid) {
      periodLoading.value = true;
      try {
        const payload = {
          start_time_timestamp: Number(periodForm.value.startTime),
          end_time_timestamp: Number(periodForm.value.endTime),
        };
        const response = await api.setVotingPeriod(payload);
        if (response.data.success) {
          // 更新成功消息以包含自动调度信息
          let successMsg = '投票周期设置成功！ TX: ' + response.data.txHash;
          if (response.data.auto_start_job_id) {
            successMsg += ` 自动启动任务已安排/更新 (ID: ${response.data.auto_start_job_id} at ${response.data.auto_start_scheduled_at}).`;
          } else if (response.data.scheduling_error) {
            successMsg += ` 注意：自动启动任务调度失败: ${response.data.scheduling_error}`;
          }
          ElMessage.success(successMsg);
          await fetchContractStatus(); // 刷新状态，会获取最新的 candidates_count
        } else {
          ElMessage.error(response.data.message || '设置投票周期失败。');
        }
      } catch (error) {
        console.error('Error setting voting period:', error);
        ElMessage.error(error.response?.data?.message || error.message || '设置投票周期时发生错误。');
      } finally {
        periodLoading.value = false;
      }
    }
  });
};

const handleStartVoting = async () => {
  startLoading.value = true;
  try {
    const response = await api.startVoting();
    if (response.data.success) {
      ElMessage.success('投票启动成功！ TX: ' + response.data.txHash);
      await fetchContractStatus();
    } else {
      ElMessage.error(response.data.message || '启动投票失败。');
    }
  } catch (error) {
    console.error('Error starting voting:', error);
    ElMessage.error(error.response?.data?.message || error.message || '启动投票时发生错误。');
  } finally {
    startLoading.value = false;
  }
};

const handleExtendDeadline = async () => {
  if (!extendFormRef.value) return;
  extendFormRef.value.validate(async (valid) => {
    if (valid) {
      extendLoading.value = true;
      try {
        const payload = {
          new_end_time_timestamp: Number(extendForm.value.newEndTime),
        };
        const response = await api.extendVotingDeadline(payload);
        if (response.data.success) {
          ElMessage.success('投票截止时间延长成功！ TX: ' + response.data.txHash);
          await fetchContractStatus();
        } else {
          ElMessage.error(response.data.message || '延长截止时间失败。');
        }
      } catch (error) {
        console.error('Error extending deadline:', error);
        ElMessage.error(error.response?.data?.message || error.message || '延长截止时间时发生错误。');
      } finally {
        extendLoading.value = false;
      }
    }
  });
};

const handleEndVoting = async () => {
  endLoading.value = true;
  try {
    const response = await api.endVoting();
    if (response.data.success) {
      ElMessage.success('投票已成功结束！ TX: ' + response.data.txHash);
      await fetchContractStatus();
    } else {
      ElMessage.error(response.data.message || '结束投票失败。');
    }
  } catch (error) {
    console.error('Error ending voting:', error);
    ElMessage.error(error.response?.data?.message || error.message || '结束投票时发生错误。');
  } finally {
    endLoading.value = false;
  }
};

const formatTimestamp = (timestamp) => {
  if (!timestamp || timestamp === 0) return 'N/A';
  // ElDatePicker 的 value-format="X" 返回的是秒级字符串，需要转为数字
  return new Date(Number(timestamp) * 1000).toLocaleString();
};

const getPhaseTagType = (phase) => {
  if (phase === 'Pending') return 'info';
  if (phase === 'Active') return 'success';
  if (phase === 'Concluded') return 'danger';
  return '';
};

onMounted(() => {
  fetchContractStatus();
});

</script>

<style scoped>
.manage-voting-activity-container {
  padding: 20px;
}
.page-header {
  margin-bottom: 20px;
  padding-left: 0;
  padding-right: 0;
}
.page-header h2 {
  margin-bottom: 10px;
}
.status-card, .actions-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.action-section {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}
.action-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.action-section h4 {
  margin-bottom: 15px;
  font-size: 1.1em;
}
.el-form {
    max-width: 500px;
}
</style>