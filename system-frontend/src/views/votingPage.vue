<template>
    <el-container class="voting-page-container">
        <el-header height="auto" class="page-header">
            <h2>在线投票</h2>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
                <el-breadcrumb-item>投票页面</el-breadcrumb-item>
            </el-breadcrumb>
        </el-header>

        <el-main>
            <el-card shadow="never">
                <template #header>
                    <div class="card-header">
                        <span>{{ pageTitle }}</span>
                        <el-button type="primary" :icon="Refresh" @click="loadPageData"
                            :loading="loadingData">刷新状态</el-button>
                    </div>
                </template>

                <!-- 投票状态和截止时间 -->
                <div v-if="votingStatusInfo" class="status-section">
                    <p>
                        当前投票阶段: <el-tag :type="getPhaseTagType(votingStatusInfo.phase)">{{ votingStatusInfo.phase
                            }}</el-tag>
                    </p>
                    <p v-if="votingStatusInfo.startTime > 0">开始时间: {{ formatDateTime(votingStatusInfo.startTime) }}</p>
                    <p v-if="votingStatusInfo.endTime > 0">结束时间: {{ formatDateTime(votingStatusInfo.endTime) }}</p>
                </div>
                <el-skeleton :rows="2" animated v-if="loadingStatus" />

                <!-- 用户投票状态提示 -->
                <el-alert
                    v-if="!loadingData && currentUser && hasVoted && votingStatusInfo && votingStatusInfo.phase === 'Active'"
                    title="您已经参与过本次投票" type="success" description="感谢您的参与！如果您需要更改选择，请先撤销当前投票。" show-icon
                    :closable="false" style="margin-bottom: 20px;" />

                <!-- 候选人列表与投票操作 -->
                <div v-if="votingStatusInfo && votingStatusInfo.phase === 'Active' && candidates.length > 0"
                    class="candidates-section">
                    <h3>{{ hasVoted ? '您可以撤销或查看您的选择' : '请选择您支持的候选人：' }}</h3>

                    <!-- 使用 el-row 和 el-col 进行布局 -->
                    <el-row :gutter="20" class="candidates-row">
                        <el-col v-for="candidate in candidates" :key="candidate.id_on_chain" :xs="24" :sm="12" :md="8"
                            class="candidate-col">
                            <el-card shadow="hover" class="candidate-card" :body-style="{ padding: '0px' }"
                                :class="{ 'is-selected': selectedCandidateIndex === candidate.id_on_chain, 'is-disabled': hasVoted && !allowReselectAfterVote }"
                                @click="selectCandidate(candidate.id_on_chain)">
                                <el-image :src="candidate.image_url || defaultCandidateImage" fit="cover"
                                    class="candidate-image" lazy>
                                    <template #error>
                                        <div class="image-slot">
                                            <el-icon>
                                                <Picture />
                                            </el-icon>
                                            <span>图片加载失败</span>
                                        </div>
                                    </template>
                                </el-image>
                                <div class="candidate-info">
                                    <h4 class="candidate-name">{{ candidate.name }}</h4>
                                    <p class="candidate-slogan" :title="candidate.slogan || '暂无口号'">
                                        {{ candidate.slogan || '暂无口号' }}
                                    </p>
                                    <p class="candidate-description" :title="candidate.description || '暂无描述'">
                                        {{ truncateText(candidate.description, 50) || '暂无描述' }}
                                    </p>
                                    <div class="candidate-vote-count">
                                        当前票数: <el-tag size="small" type="info">{{ candidate.vote_count_from_chain || 0
                                            }}</el-tag>
                                    </div>
                                    <el-radio :label="candidate.id_on_chain" size="large" border class="candidate-radio"
                                        :disabled="hasVoted && !allowReselectAfterVote">
                                        {{ selectedCandidateIndex === candidate.id_on_chain ? '已选择' : '选择该候选人' }}
                                    </el-radio>
                                </div>
                            </el-card>
                        </el-col>
                    </el-row>


                    <div style="margin-top: 30px; text-align: center;">
                        <el-button v-if="!hasVoted" type="primary" @click="submitVote"
                            :disabled="selectedCandidateIndex === null || submittingVote" :loading="submittingVote"
                            size="large">
                            确认投票
                        </el-button>
                        <el-button v-if="hasVoted" type="warning" @click="revokeCurrentVote" :loading="revokingVote"
                            size="large">
                            撤销我的投票
                        </el-button>
                    </div>
                </div>

                <!-- 投票未开始或已结束等状态 -->
                <el-empty
                    v-if="!loadingData && ((votingStatusInfo && votingStatusInfo.phase !== 'Active') || (votingStatusInfo && votingStatusInfo.phase === 'Active' && candidates.length === 0))"
                    :description="emptyStateDescription" />

            </el-card>
        </el-main>
    </el-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '@/services/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh, Picture } from '@element-plus/icons-vue';
import defaultCandidateImage from '@/assets/candidates/logo.png';

const candidates = ref([]);
const votingStatusInfo = ref(null);
const selectedCandidateIndex = ref(null);
const currentUser = ref(null);

const loadingData = ref(true);
const loadingCandidates = ref(false);
const loadingStatus = ref(false);
const submittingVote = ref(false);
const revokingVote = ref(false);

const allowReselectAfterVote = ref(false);


const pageTitle = computed(() => {
    if (!votingStatusInfo.value) return "投票页面";
    if (votingStatusInfo.value.phase === "Pending") return "投票尚未开始";
    if (votingStatusInfo.value.phase === "Concluded") return "投票已结束";
    if (votingStatusInfo.value.phase === "Active") {
        return hasVoted.value ? "您已投票" : "进行投票";
    }
    return "投票页面";
});

const hasVoted = computed(() => {
    return currentUser.value?.has_voted === true;
});

const canPerformVoteAction = computed(() => {
    return votingStatusInfo.value && votingStatusInfo.value.phase === 'Active';
});

const emptyStateDescription = computed(() => {
    if (loadingData.value) return "正在加载数据...";
    if (!votingStatusInfo.value) return "无法获取投票状态。";
    if (votingStatusInfo.value.phase === "Pending") return "投票尚未开始，请耐心等待。";
    if (votingStatusInfo.value.phase === "Concluded") return "本次投票已结束。";
    if (candidates.value.length === 0 && votingStatusInfo.value.phase === "Active") return "当前没有候选人可供投票。";
    return "投票当前不可用。";
});

const truncateText = (text, maxLength) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
};

const fetchCurrentUser = async () => {
    try {
        const response = await api.getCurrentUserProfile();
        if (response.data.success) {
            currentUser.value = response.data.user;
            console.log("Current user data (including has_voted):", currentUser.value);
        } else {
            ElMessage.error('获取用户信息失败: ' + response.data.message);
            currentUser.value = null;
        }
    } catch (error) {
        console.error("Error fetching current user:", error);
        ElMessage.error('获取用户信息时发生网络错误。');
        currentUser.value = null;
    }
};


const fetchCandidates = async () => {
    loadingCandidates.value = true;
    try {
        const response = await api.getAllCandidates(); // 这个API应返回包含 description, slogan 等字段
        if (response.data.success) {
            candidates.value = response.data.candidates;
        } else {
            ElMessage.error('获取候选人列表失败: ' + response.data.message);
            candidates.value = [];
        }
    } catch (error) {
        console.error("Error fetching candidates:", error);
        ElMessage.error('获取候选人列表时发生网络错误。');
        candidates.value = [];
    } finally {
        loadingCandidates.value = false;
    }
};

const fetchVotingStatus = async () => {
    loadingStatus.value = true;
    try {
        const response = await api.getVotingStatus();
        if (response.data.success) {
            votingStatusInfo.value = response.data;
        } else {
            ElMessage.error('获取投票状态失败: ' + response.data.message);
            votingStatusInfo.value = null;
        }
    } catch (error) {
        console.error('Error fetching voting status:', error);
        ElMessage.error('获取投票状态时发生网络错误。');
        votingStatusInfo.value = null;
    } finally {
        loadingStatus.value = false;
    }
};

const loadPageData = async () => {
    loadingData.value = true;
    selectedCandidateIndex.value = null;
    await Promise.all([
        fetchCurrentUser(),
        fetchVotingStatus(),
        fetchCandidates()
    ]);
    loadingData.value = false;
};

const selectCandidate = (candidateIndex) => {
    if (canPerformVoteAction.value && (!hasVoted.value || allowReselectAfterVote.value)) {
        selectedCandidateIndex.value = candidateIndex;
    }
};

const submitVote = async () => {
    if (selectedCandidateIndex.value === null) {
        ElMessage.warning('请先选择一位候选人。');
        return;
    }
    if (hasVoted.value) {
        ElMessage.info('您已经投过票了。如需更改，请先撤销投票。');
        return;
    }

    ElMessageBox.confirm(
        `您确定要投票给候选人 "${candidates.value.find(c => c.id_on_chain === selectedCandidateIndex.value)?.name}" 吗？`,
        '确认投票',
        {
            confirmButtonText: '确定投票',
            cancelButtonText: '取消',
            type: 'warning',
        }
    ).then(async () => {
        submittingVote.value = true;
        try {
            const payload = { candidate_index_on_chain: selectedCandidateIndex.value };
            const response = await api.castVote(payload);
            if (response.data.success) {
                ElMessage.success('投票成功！感谢您的参与。TX: ' + response.data.txHash);
                await loadPageData();
            } else {
                ElMessage.error('投票失败: ' + (response.data.message || '未知错误'));
                if (response.data.message && response.data.message.toLowerCase().includes('already voted')) {
                    await fetchCurrentUser();
                }
            }
        } catch (error) {
            console.error("Error casting vote:", error);
            const errorMsg = error.response?.data?.message || error.message || '投票时发生错误。';
            ElMessage.error('投票失败: ' + errorMsg);
            if (error.response?.data?.message && error.response.data.message.toLowerCase().includes('already voted')) {
                await fetchCurrentUser();
            }
        } finally {
            submittingVote.value = false;
        }
    }).catch(() => {
        ElMessage.info('投票已取消。');
    });
};

const revokeCurrentVote = async () => {
    if (!hasVoted.value) {
        ElMessage.info('您尚未投票，无需撤销。');
        return;
    }
    ElMessageBox.confirm(
        `您确定要撤销当前的投票吗？撤销后您可以重新投票（如果投票仍在进行中）。`,
        '确认撤销投票',
        {
            confirmButtonText: '确定撤销',
            cancelButtonText: '取消',
            type: 'warning',
        }
    ).then(async () => {
        revokingVote.value = true;
        try {
            const response = await api.revokeVote();
            if (response.data.success) {
                ElMessage.success('投票已成功撤销。您可以重新投票。TX: ' + response.data.txHash);
                await loadPageData();
            } else {
                ElMessage.error('撤销投票失败: ' + (response.data.message || '未知错误'));
            }
        } catch (error) {
            console.error("Error revoking vote:", error);
            const errorMsg = error.response?.data?.message || error.message || '撤销投票时发生错误。';
            ElMessage.error('撤销投票失败: ' + errorMsg);
        } finally {
            revokingVote.value = false;
        }
    }).catch(() => {
        ElMessage.info('撤销投票已取消。');
    });
};


const formatDateTime = (timestamp) => {
    if (!timestamp || timestamp === 0) return 'N/A';
    return new Date(Number(timestamp) * 1000).toLocaleString();
};

const getPhaseTagType = (phase) => {
    if (phase === 'Pending') return 'info';
    if (phase === 'Active') return 'success';
    if (phase === 'Concluded') return 'error';
    return '';
};

onMounted(() => {
    loadPageData();
});
</script>

<style scoped>
.voting-page-container {
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

.status-section {
    margin-bottom: 20px;
    padding: 10px;
    background-color: #f4f4f5;
    border-radius: 4px;
}

.status-section p {
    margin: 5px 0;
}

.candidates-section h3 {
    margin-bottom: 20px;
    /* 增加标题和候选人卡片之间的间距 */
    text-align: center;
}

/* 候选人行布局 */
.candidates-row {
    display: flex;
    flex-wrap: wrap;
    /* 允许换行 */
    /* justify-content: flex-start;  如果希望不足3个时靠左对齐，可以使用这个 */
}

.candidate-col {
    margin-bottom: 20px;
    /* 候选人卡片之间的垂直间距 */
    display: flex;
    /* 使 el-col 成为 flex 容器，让内部卡片可以撑满 */
}

.candidate-card {
    cursor: pointer;
    transition: box-shadow 0.3s, border-color 0.3s;
    width: 100%;
    /* 卡片宽度占满 el-col */
    display: flex;
    /* 使卡片成为 flex 容器 */
    flex-direction: column;
    /* 垂直排列图片和信息 */
}

.candidate-card:hover:not(.is-disabled) {
    box-shadow: var(--el-box-shadow-dark);
}

.candidate-card.is-selected:not(.is-disabled) {
    border-color: var(--el-color-primary);
    box-shadow: 0 0 15px rgba(var(--el-color-primary-rgb), 0.5);
}

.candidate-card.is-disabled {
    cursor: not-allowed;
    opacity: 0.7;
}

.candidate-image {
    width: 100%;
    height: 200px;
    display: block;
    object-fit: cover;
    /* 确保图片覆盖区域，不变形 */
}

.image-slot {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 100%;
    background: #f5f7fa;
    color: #c0c4cc;
    font-size: 14px;
}

.image-slot .el-icon {
    font-size: 30px;
    margin-bottom: 5px;
}

.candidate-info {
    padding: 15px;
    flex-grow: 1;
    /* 让信息区域占据剩余空间 */
    display: flex;
    flex-direction: column;
    /* 垂直排列信息项 */
    justify-content: space-between;
    /* 使radio按钮靠底 */
}

.candidate-name {
    font-size: 1.2em;
    /* 稍大一点的姓名 */
    font-weight: bold;
    display: block;
    margin-bottom: 8px;
    line-height: 1.2;
}

.candidate-slogan {
    font-size: 0.95em;
    color: #555;
    margin-bottom: 8px;
    min-height: 3em;
    /* 约等于2行文字的高度 */
    line-height: 1.5;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    /* 最多显示两行 */
    line-clamp: 2; 
    /* 标准属性 */
    -webkit-box-orient: vertical;
}

.candidate-description {
    font-size: 0.85em;
    color: #777;
    margin-bottom: 10px;
    min-height: 2.5em;
    /* 约等于2行文字的高度 */
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2; 
    /* 最多显示两行 */
    line-clamp: 2;
    /* 标准属性 */
    -webkit-box-orient: vertical;
}

.candidate-vote-count {
    font-size: 0.9em;
    color: #606266;
    margin-bottom: 12px;
}

.candidate-radio {
    width: 100%;
    margin-top: auto;
    /* 将radio按钮推到底部 */
}
</style>