<template>
    <el-container class="manage-applications-container">
        <el-header height="auto" class="page-header">
            <h2>管理选民申请</h2>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
                <el-breadcrumb-item :to="{ path: '/admin' }">管理员</el-breadcrumb-item>
                <el-breadcrumb-item>管理选民申请</el-breadcrumb-item>
            </el-breadcrumb>
        </el-header>

        <el-main>
            <el-card shadow="never">
                <template #header>
                    <div class="card-header">
                        <span>选民申请列表</span>
                        <div>
                            <el-select v-model="filterStatus" placeholder="筛选状态" @change="fetchApplications"
                                style="margin-right: 10px; width: 150px;">
                                <el-option label="全部" value="all"></el-option>
                                <el-option label="待处理" value="pending"></el-option>
                                <el-option label="已批准" value="approved"></el-option>
                                <el-option label="已拒绝" value="rejected"></el-option>
                            </el-select>
                            <el-button type="primary" :icon="Refresh" @click="fetchApplications"
                                :loading="loading">刷新列表</el-button>
                        </div>
                    </div>
                </template>

                <el-table :data="applications" v-loading="loading" style="width: 100%" empty-text="暂无选民申请">
                    <el-table-column type="expand">
                        <template #default="props">
                            <div style="padding: 10px 20px;">
                                <p><strong>申请ID:</strong> {{ props.row.id }}</p>
                                <p><strong>用户ID (数据库):</strong> {{ props.row.user_id }}</p>
                                <!-- <p><strong>管理员备注:</strong> {{ props.row.admin_notes || '无' }}</p> --> {/* Removed
                                admin_notes display */}
                                <p v-if="props.row.reviewed_by_admin_userid"><strong>审核管理员:</strong> {{
                                    props.row.reviewed_by_admin_userid }}</p>
                                <p v-if="props.row.reviewed_at"><strong>审核时间:</strong> {{
                                    formatDateTime(props.row.reviewed_at) }}</p>
                            </div>
                        </template>
                    </el-table-column>
                    <el-table-column prop="user_userid" label="申请用户" width="150" sortable />
                    <el-table-column prop="user_ethereum_address" label="用户ETH地址" width="320" />
                    <el-table-column label="申请状态" width="120" sortable>
                        <template #default="scope">
                            <el-tag :type="getStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column label="提交时间" width="180" sortable>
                        <template #default="scope">
                            {{ formatDateTime(scope.row.submitted_at) }}
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width="200" fixed="right" align="center">
                        <template #default="scope">
                            <div v-if="scope.row.status === 'pending'">
                                <el-button size="small" type="success"
                                    @click="openReviewDialog(scope.row, 'approved')">批准</el-button>
                                <el-button size="small" type="danger"
                                    @click="openReviewDialog(scope.row, 'rejected')">拒绝</el-button>
                            </div>
                            <span v-else>已处理</span>
                        </template>
                    </el-table-column>
                </el-table>

                <el-pagination v-if="totalApplications > 0" background layout="total, sizes, prev, pager, next, jumper"
                    :total="totalApplications" :page-sizes="[10, 20, 50, 100]" :current-page="currentPage"
                    :page-size="pageSize" @size-change="handleSizeChange" @current-change="handleCurrentChange"
                    style="margin-top: 20px; text-align: right;" />
            </el-card>
        </el-main>

        <!-- 审核对话框 -->
        <el-dialog v-model="reviewDialogVisible" :title="`审核选民申请 - ${reviewAction === 'approved' ? '批准' : '拒绝'}`"
            width="clamp(300px, 40%, 500px)" @close="resetReviewDialog" :close-on-click-modal="false" append-to-body>
            <!-- <el-form ref="reviewFormRef" :model="reviewForm" label-width="80px"> -->
            <p style="margin-bottom:15px;">
                确定要<strong>{{ reviewAction === 'approved' ? '批准' : '拒绝' }}</strong>用户
                <strong>{{ currentApplication?.user_userid }}</strong>
                (ETH: {{ currentApplication?.user_ethereum_address || '未提供' }}) 的选民申请吗？
            </p>
            <!-- 
          <el-form-item label="审核备注" prop="admin_notes">
            <el-input type="textarea" :rows="3" v-model="reviewForm.admin_notes" placeholder="请输入管理员备注 (可选)" />
          </el-form-item> 
          -->
            <!-- </el-form> -->
            <template #footer>
                <span class="dialog-footer">
                    <el-button @click="reviewDialogVisible = false">取消</el-button>
                    <el-button :type="reviewAction === 'approved' ? 'success' : 'danger'" @click="submitReview"
                        :loading="reviewSubmitting">
                        确认{{ reviewAction === 'approved' ? '批准' : '拒绝' }}
                    </el-button>
                </span>
            </template>
        </el-dialog>
    </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'; // Removed reactive as reviewForm is no longer complex
import api from '@/services/api';
import { ElMessage } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';

const applications = ref([]);
const loading = ref(true);
const filterStatus = ref('pending');

const currentPage = ref(1);
const pageSize = ref(10);
const totalApplications = ref(0);

const reviewDialogVisible = ref(false);
const reviewSubmitting = ref(false);
// const reviewFormRef = ref(null); // No longer needed
const currentApplication = ref(null);
const reviewAction = ref('');

// const reviewForm = reactive({ // No longer needed
//   admin_notes: '',
// });

const fetchApplications = async () => {
    loading.value = true;
    try {
        const response = await api.getVoterApplications(filterStatus.value, currentPage.value, pageSize.value);
        if (response.data.success) {
            applications.value = response.data.applications;
            totalApplications.value = response.data.total;
        } else {
            ElMessage.error('获取选民申请列表失败: ' + response.data.message);
            applications.value = [];
            totalApplications.value = 0;
        }
    } catch (error) {
        console.error("Error fetching voter applications:", error);
        ElMessage.error('获取选民申请列表时发生网络或服务器错误。');
        applications.value = [];
        totalApplications.value = 0;
    } finally {
        loading.value = false;
    }
};

const handleSizeChange = (val) => {
    pageSize.value = val;
    currentPage.value = 1;
    fetchApplications();
};

const handleCurrentChange = (val) => {
    currentPage.value = val;
    fetchApplications();
};

const getStatusTagType = (status) => {
    switch (status) {
        case 'pending':
            return 'warning';
        case 'approved':
            return 'success';
        case 'rejected':
            return 'danger';
        default:
            return 'info';
    }
};

const formatDateTime = (dateTimeString) => {
    if (!dateTimeString) return 'N/A';
    return new Date(dateTimeString).toLocaleString();
};

const openReviewDialog = (application, action) => {
    currentApplication.value = application;
    reviewAction.value = action;
    // reviewForm.admin_notes = ''; // No longer needed
    reviewDialogVisible.value = true;
};

const resetReviewDialog = () => {
    reviewDialogVisible.value = false;
    currentApplication.value = null;
    // reviewForm.admin_notes = ''; // No longer needed
    // if (reviewFormRef.value) { // No longer needed
    //   reviewFormRef.value.resetFields();
    // }
};

const submitReview = async () => {
    reviewSubmitting.value = true;
    try {
        const payload = {
            status: reviewAction.value,
            // admin_notes: reviewForm.admin_notes, // Removed admin_notes from payload
        };
        // 如果后端 API 严格要求 admin_notes 字段，即使为空，你可能需要发送 admin_notes: ''
        // 但根据你提供的 models.py，后端在 review_voter_application 中只是 data.get('admin_notes', '')
        // 这意味着如果前端不发送 admin_notes，它会默认为空字符串，这应该是可以的。
        // 如果后端接口严格要求该字段，则应发送： admin_notes: ''

        const response = await api.reviewVoterApplication(currentApplication.value.id, payload);
        if (response.data.success) {
            ElMessage.success(`申请已成功${reviewAction.value === 'approved' ? '批准' : '拒绝'}!`);
            resetReviewDialog();
            await fetchApplications();
        } else {
            ElMessage.error(`审核失败: ${response.data.message || '未知错误'}`);
        }
    } catch (error) {
        console.error("Error submitting review:", error);
        const errorMsg = error.response?.data?.message || error.message || '审核时发生错误。';
        ElMessage.error(`审核失败: ${errorMsg}`);
    } finally {
        reviewSubmitting.value = false;
    }
};

onMounted(() => {
    fetchApplications();
});
</script>

<style scoped>
.manage-applications-container {
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

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 1.1em;
    font-weight: 500;
}

:deep(.el-dialog__body) {
    padding-top: 10px;
    padding-bottom: 0;
}

.dialog-footer {
    text-align: right;
}
</style>