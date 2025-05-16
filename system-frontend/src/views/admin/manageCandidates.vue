<template>
  <el-container class="manage-candidates-container">
    <el-header height="auto" class="page-header">
      <h2>管理候选人</h2>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: '/admin' }">管理员</el-breadcrumb-item>
        <el-breadcrumb-item>管理候选人</el-breadcrumb-item>
      </el-breadcrumb>
    </el-header>

    <el-main>
      <!-- 投票状态提示卡片 -->
      <el-card class="status-card" shadow="never" v-if="votingStatus">
        <template #header>
          <div class="card-header">
            <span>当前投票状态</span>
            <el-button type="primary" :icon="Refresh" @click="fetchVotingStatus" :loading="statusLoading" size="small">
              刷新状态
            </el-button>
          </div>
        </template>
        <el-alert 
          v-if="votingStatus.phase !== 'Pending'" 
          :title="`当前投票阶段：${votingStatus.phase}`" 
          :description="`在当前阶段（${votingStatus.phase}）不允许添加新候选人。只有在投票处于'Pending'阶段时才能添加候选人。`"
          type="warning" 
          show-icon 
          :closable="false"
          style="margin-bottom: 15px;">
        </el-alert>
        <el-alert 
          v-else 
          title="投票处于待处理阶段" 
          description="您可以添加新的候选人。一旦投票开始，将无法再添加候选人。"
          type="success" 
          show-icon 
          :closable="false"
          style="margin-bottom: 15px;">
        </el-alert>
      </el-card>

      <!-- 候选人列表卡片 -->
      <el-card class="candidates-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>候选人列表</span>
            <el-button 
              type="primary" 
              @click="openAddDialog" 
              :disabled="!canAddCandidate"
              title="仅在投票未开始前可添加候选人">
              <el-icon><Plus /></el-icon> 添加候选人
            </el-button>
          </div>
        </template>

        <el-table 
          :data="candidates" 
          v-loading="candidatesLoading" 
          style="width: 100%" 
          empty-text="暂无候选人数据"
          border>
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="id" label="数据库ID" width="100" sortable />
          <el-table-column prop="id_on_chain" label="链上索引" width="100" sortable />
          <el-table-column prop="name" label="姓名" width="180" sortable />
          <el-table-column prop="description" label="描述" min-width="200">
            <template #default="scope">
              <span style="white-space: pre-wrap;">{{ scope.row.description || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="slogan" label="口号" min-width="150">
            <template #default="scope">
              <span>{{ scope.row.slogan || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="图片" width="120" align="center">
            <template #default="scope">
              <el-image 
                style="width: 80px; height: 80px; border-radius: 4px;" 
                :src="scope.row.image_url || defaultImageUrl" 
                :preview-src-list="[scope.row.image_url || defaultImageUrl]" 
                fit="cover"
                lazy>
                <template #error>
                  <div class="image-slot">
                    加载失败
                  </div>
                </template>
              </el-image>
            </template>
          </el-table-column>
          <el-table-column prop="vote_count_from_chain" label="获得票数" width="100" sortable>
            <template #default="scope">
              <el-tag type="info">{{ scope.row.vote_count_from_chain || 0 }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-main>

    <!-- 添加候选人对话框 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加新候选人"
      width="500px"
      @close="resetFormDialog"
      :close-on-click-modal="false"
      append-to-body>
      <el-form 
        ref="candidateFormRef" 
        :model="candidateForm" 
        :rules="formRules" 
        label-width="100px" 
        style="max-width: 450px; margin: 0 auto;">
        <el-form-item label="候选人姓名" prop="name">
          <el-input v-model="candidateForm.name" placeholder="请输入候选人姓名" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input 
            type="textarea" 
            :rows="3" 
            v-model="candidateForm.description" 
            placeholder="请输入候选人描述（可选）" />
        </el-form-item>
        <el-form-item label="口号" prop="slogan">
          <el-input v-model="candidateForm.slogan" placeholder="请输入候选人口号（可选）" />
        </el-form-item>
        <el-form-item label="候选人图片" prop="image_file">
          <el-upload
            class="avatar-uploader"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleImageChange"
            action="#"
            accept="image/jpeg,image/png,image/gif"
          >
            <img v-if="imageUrl" :src="imageUrl" class="avatar" />
            <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            <div class="el-upload__tip" style="margin-top: 8px;">点击上传候选人图片，支持JPG/PNG格式</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitCandidateForm" :loading="submitting">
            提交
          </el-button>
        </span>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import api from '@/services/api';
import { ElMessage } from 'element-plus';
import { Plus, Refresh } from '@element-plus/icons-vue';

// 默认图片路径
const defaultImageUrl = require('@/assets/candidates/logo.png');

// 数据定义
const candidates = ref([]);
const candidatesLoading = ref(true);
const addDialogVisible = ref(false);
const submitting = ref(false);
const candidateFormRef = ref(null);
const statusLoading = ref(false);
const votingStatus = ref(null);
const imageUrl = ref(''); // 预览图片URL
const imageFile = ref(null); // 图片文件对象

// 表单数据和规则
const candidateForm = ref({
  name: '',
  description: '',
  slogan: '',
  image_file: null // 改为存储文件对象而不是URL
});

const formRules = {
  name: [
    { required: true, message: '请输入候选人姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度应在2到50个字符之间', trigger: 'blur' }
  ],
  image_file: [
    { required: false, message: '请上传候选人图片', trigger: 'change' }
  ]
};

// 计算属性 - 是否可以添加候选人
const canAddCandidate = computed(() => {
  return votingStatus.value && votingStatus.value.phase === 'Pending';
});

// 方法
const fetchVotingStatus = async () => {
  statusLoading.value = true;
  try {
    const response = await api.getContractVotingStatus();
    if (response.data.success) {
      votingStatus.value = response.data;
    } else {
      ElMessage.error(response.data.message || '获取投票状态失败');
    }
  } catch (error) {
    console.error('Error fetching voting status:', error);
    ElMessage.error('获取投票状态时发生网络错误');
  } finally {
    statusLoading.value = false;
  }
};

const fetchCandidates = async () => {
  candidatesLoading.value = true;
  try {
    const response = await api.getAllCandidates();
    if (response.data.success) {
      candidates.value = response.data.candidates;
    } else {
      ElMessage.error(response.data.message || '获取候选人列表失败');
      candidates.value = [];
    }
  } catch (error) {
    console.error('Error fetching candidates:', error);
    ElMessage.error('获取候选人列表时发生网络错误');
    candidates.value = [];
  } finally {
    candidatesLoading.value = false;
  }
};

// 处理图片变更
const handleImageChange = (uploadFile) => {
  // 检查uploadFile是否是预期的对象
  if (!uploadFile) {
    ElMessage.error('文件对象无效');
    return false;
  }
  
  // Element-Plus中，uploadFile可能是包含raw属性的对象，而不是直接的File对象
  const file = uploadFile.raw || uploadFile;
  
  // 确保file和file.type存在
  if (!file || !file.type) {
    ElMessage.error('文件格式不正确或无法识别');
    return false;
  }
  
  const isImage = file.type.startsWith('image/');
  const isLt2M = file.size / 1024 / 1024 < 2;

  if (!isImage) {
    ElMessage.error('上传图片只能是图片格式!');
    return false;
  }
  if (!isLt2M) {
    ElMessage.error('上传图片大小不能超过 2MB!');
    return false;
  }
  
  imageFile.value = file;
  candidateForm.value.image_file = file;
  imageUrl.value = URL.createObjectURL(file);
};

const openAddDialog = () => {
  if (!canAddCandidate.value) {
    ElMessage.warning(`当前投票阶段为 '${votingStatus.value?.phase}'，不能添加候选人。`);
    return;
  }
  addDialogVisible.value = true;
  nextTick(() => {
    if (candidateFormRef.value) {
      candidateFormRef.value.resetFields();
    }
  });
};

const resetFormDialog = () => {
  if (candidateFormRef.value) {
    candidateFormRef.value.resetFields();
  }
  candidateForm.value = {
    name: '',
    description: '',
    slogan: '',
    image_file: null
  };
  imageUrl.value = '';
  imageFile.value = null;
};

const uploadImage = async () => {
  if (!imageFile.value) return null;
  
  try {
    // 创建表单数据对象
    const formData = new FormData();
    formData.append('file', imageFile.value);
    
    // 调用上传API
    const response = await api.uploadCandidateImage(formData);
    if (response.data.success) {
      return response.data.image_url; // 返回服务器上的图片URL
    } else {
      throw new Error(response.data.message || '图片上传失败');
    }
  } catch (error) {
    console.error('Error uploading image:', error);
    throw error;
  }
};

const submitCandidateForm = async () => {
  if (!candidateFormRef.value) return;
  
  await candidateFormRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true;
      try {
        let imageUrl = null;
        
        // 上传图片（如果有）
        if (imageFile.value) {
          imageUrl = await uploadImage();
        }
        
        // 准备候选人数据
        const candidateData = {
          name: candidateForm.value.name,
          description: candidateForm.value.description,
          slogan: candidateForm.value.slogan,
          image_url: imageUrl // 使用上传后的图片URL
        };
        
        // 提交候选人信息
        const response = await api.addCandidate(candidateData);
        if (response.data.success) {
          ElMessage.success('候选人添加成功!');
          addDialogVisible.value = false;
          resetFormDialog();
          await fetchCandidates(); // 刷新候选人列表
        } else {
          ElMessage.error('添加候选人失败: ' + (response.data.message || '未知错误'));
        }
      } catch (error) {
        console.error('Error submitting candidate:', error);
        const errorMsg = error.response?.data?.message || error.message || '添加候选人时发生错误';
        ElMessage.error('添加候选人失败: ' + errorMsg);
      } finally {
        submitting.value = false;
      }
    } else {
      ElMessage.warning('请正确填写表单信息');
    }
  });
};

// 生命周期钩子
onMounted(async () => {
  await fetchVotingStatus();
  await fetchCandidates();
});
</script>

<style scoped>
.manage-candidates-container {
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

.status-card, 
.candidates-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1.1em;
  font-weight: 500;
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
  font-size: 14px;
}

/* 图片上传相关样式 */
.avatar-uploader {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.avatar-uploader .avatar {
  width: 178px;
  height: 178px;
  display: block;
  object-fit: cover;
}
.avatar-uploader .el-upload {
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 178px;
  height: 178px;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
}

:deep(.el-dialog__body) {
  padding-top: 10px;
}
</style>