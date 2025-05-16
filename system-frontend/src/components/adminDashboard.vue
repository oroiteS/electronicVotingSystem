// src/components/adminDashboard.vue
<template>
    <el-card class="admin-dashboard-card" shadow="never">
        <template #header>
            <div class="card-header">
                <span>管理员控制台</span>
            </div>
        </template>
        <el-alert title="管理员专属区域" type="info" description="您可以在这里管理选举的各个方面。" show-icon :closable="false"
            style="margin-bottom: 20px;" />
        <el-row :gutter="20">
            <el-col :xs="24" :sm="12" :md="8">
                <el-card shadow="hover" class="action-card" @click="navigateTo('/admin/candidates')">
                    <div class="action-card-content">
                        <el-icon :size="30" color="#409EFC">
                            <Management />
                        </el-icon>
                        <h4>管理候选人</h4>
                        <p>添加、查看和编辑候选人信息。</p>
                    </div>
                </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8">
                <el-card shadow="hover" class="action-card" @click="navigateTo('/admin/applications')">
                    <div class="action-card-content">
                        <el-icon :size="30" color="#67C23A">
                            <User />
                        </el-icon>
                        <h4>管理选民申请</h4>
                        <p>审核待处理的选民资格申请。</p>
                    </div>
                </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8">
                <el-card shadow="hover" class="action-card" @click="navigateTo('/admin/voting')">
                    <div class="action-card-content">
                        <el-icon :size="30" color="#E6A23C">
                            <Opportunity />
                        </el-icon>
                        <h4>管理投票活动</h4>
                        <p>设置投票周期，启动/结束投票，查看状态。</p>
                    </div>
                </el-card>
            </el-col>
            <!-- 可以在这里添加更多的管理员功能卡片 -->
        </el-row>
    </el-card>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { Management, User, Opportunity } from '@element-plus/icons-vue';

const router = useRouter();

const navigateTo = (path) => {
    router.push(path);
};
</script>

<style scoped>
.admin-dashboard-card {
    margin-top: 20px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 1.1em;
}

.action-card {
    cursor: pointer;
    text-align: center;
    margin-bottom: 20px;
}

.action-card:hover {
    border-color: #409EFC;
    /* Element Plus 主题色 */
}

.action-card-content {
    padding: 20px;
}

.action-card-content h4 {
    margin: 10px 0;
}

.action-card-content p {
    font-size: 0.9em;
    color: #909399;
}
</style>