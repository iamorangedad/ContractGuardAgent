const API_BASE = '';

const sampleOriginal = `采购合同

甲方（供应商）：北京科技有限公司
乙方（采购方）：上海贸易有限公司

一、合同金额
本合同总金额为人民币100万元（大写：壹佰万元整）。

二、付款方式
1. 合同签订后5个工作日内，乙方支付合同总金额的30%作为预付款；
2. 货物交付验收合格后5个工作日内，乙方支付合同总金额的60%；
3. 质保期满后5个工作日内，乙方支付剩余10%尾款。

三、交货时间
甲方应在合同签订后30日内完成交货。

四、质量保证
1. 产品质量符合国家标准；
2. 质保期为货物验收合格之日起12个月；
3. 甲方对产品质量负责，因质量问题造成的损失由甲方承担。

五、违约责任
1. 甲方逾期交货的，每逾期一天按合同总金额的0.5%支付违约金；
2. 乙方逾期付款的，每逾期一天按应付金额的0.5%支付违约金。

六、争议解决
本合同在履行过程中发生的争议，由双方协商解决；协商不成的，提交乙方所在地人民法院诉讼解决。

七、合同生效
本合同一式两份，甲乙双方各执一份，自双方签字盖章之日起生效。`;

const sampleModified = `采购合同

甲方（供应商）：北京科技有限公司
乙方（采购方）：上海贸易有限公司

一、合同金额
本合同总金额为人民币120万元（大写：壹佰贰拾万元整）。

二、付款方式
1. 合同签订后5个工作日内，乙方支付合同总金额的50%作为预付款；
2. 货物交付验收合格后5个工作日内，乙方支付合同总金额的45%；
3. 质保期满后5个工作日内，乙方支付剩余5%尾款。

三、交货时间
甲方应在合同签订后45日内完成交货。

四、质量保证
1. 产品质量符合国家标准；
2. 质保期为货物验收合格之日起6个月；
3. 甲方对产品质量负责，因质量问题造成的损失由甲方承担。

五、违约责任
1. 甲方逾期交货的，每逾期一天按合同总金额的1%支付违约金；
2. 乙方逾期付款的，每逾期一天按应付金额的1%支付违约金。

六、争议解决
本合同在履行过程中发生的争议，由双方协商解决；协商不成的，提交北京仲裁委员会仲裁解决。

七、合同生效
本合同一式两份，甲乙双方各执一份，自双方签字盖章之日起生效。`;

document.getElementById('sampleBtn')?.addEventListener('click', function() {
    document.getElementById('originalText').value = sampleOriginal;
    document.getElementById('modifiedText').value = sampleModified;
});

document.getElementById('compareForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const originalText = document.getElementById('originalText').value.trim();
    const modifiedText = document.getElementById('modifiedText').value.trim();
    const category = document.getElementById('category').value || null;
    
    if (!originalText || !modifiedText) {
        alert('请填写合同原件和修改件内容');
        return;
    }
    
    const formData = {
        original_text: originalText,
        modified_text: modifiedText,
        category: category
    };
    
    try {
        const response = await fetch(API_BASE + '/api/contracts/compare', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error('请求失败');
        }
        
        const result = await response.json();
        
        document.getElementById('resultSection').style.display = 'block';
        updateTaskStatus(result.task_id);
        
    } catch (error) {
        alert('提交失败: ' + error.message);
    }
});

async function updateTaskStatus(taskId) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(API_BASE + '/api/contracts/status/' + taskId);
            const status = await response.json();
            
            const statusBadge = document.getElementById('statusBadge');
            const statusText = document.getElementById('statusText');
            const statusMessage = document.getElementById('statusMessage');
            const viewResultLink = document.getElementById('viewResultLink');
            
            statusBadge.className = 'badge ' + status.status;
            statusBadge.textContent = getStatusText(status.status);
            statusText.textContent = '状态: ';
            statusMessage.textContent = status.message || '';
            
            if (status.status === 'completed' || status.status === 'failed') {
                clearInterval(pollInterval);
                viewResultLink.href = '/compare?task_id=' + taskId;
                viewResultLink.style.display = 'inline-block';
            }
            
        } catch (error) {
            console.error('获取状态失败:', error);
        }
    }, 2000);
}

function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'in_progress': '分析中',
        'waiting_human': '需人工确认',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

async function checkTaskStatus(taskId) {
    let attempts = 0;
    const maxAttempts = 60;
    
    const pollInterval = setInterval(async () => {
        attempts++;
        
        try {
            const response = await fetch(API_BASE + '/api/contracts/result/' + taskId);
            const result = await response.json();
            
            if (result.status === 'completed' || result.status === 'waiting_human' || result.status === 'failed') {
                clearInterval(pollInterval);
                showResult(result);
            }
            
            if (attempts >= maxAttempts) {
                clearInterval(pollInterval);
            }
            
        } catch (error) {
            console.error('获取结果失败:', error);
        }
    }, 1500);
}

function showResult(result) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('resultContent').style.display = 'block';
    
    const statusBadge = document.getElementById('statusBadge');
    statusBadge.className = 'badge ' + result.status;
    statusBadge.textContent = getStatusText(result.status);
    
    const evaluations = result.evaluations || [];
    const greenItems = evaluations.filter(e => e.risk_level === 'green');
    const yellowItems = evaluations.filter(e => e.risk_level === 'yellow');
    const redItems = evaluations.filter(e => e.risk_level === 'red');
    
    document.getElementById('greenCount').textContent = greenItems.length;
    document.getElementById('yellowCount').textContent = yellowItems.length;
    document.getElementById('redCount').textContent = redItems.length;
    
    if (result.status === 'waiting_human' && (yellowItems.length > 0 || redItems.length > 0)) {
        showReviewForm(evaluations);
    }
    
    if (result.final_report) {
        document.getElementById('finalReport').textContent = result.final_report;
    }
}

function showReviewForm(evaluations) {
    const reviewSection = document.getElementById('reviewSection');
    const reviewItems = document.getElementById('reviewItems');
    
    const needReview = evaluations.filter(e => e.risk_level === 'yellow' || e.risk_level === 'red');
    
    if (needReview.length === 0) return;
    
    reviewItems.innerHTML = '';
    
    needReview.forEach((item, index) => {
        const diff = item.difference;
        const div = document.createElement('div');
        div.className = 'review-item ' + item.risk_level;
        
        div.innerHTML = `
            <div class="review-item-header">
                <span class="review-item-title">${item.risk_level === 'red' ? '🔴 红色风险' : '🟡 需确认'}</span>
                <span class="badge ${item.risk_level}">${item.risk_level}</span>
            </div>
            <div class="review-item-content">
                <p><strong>说明：</strong>${item.explanation}</p>
                <p><strong>建议：</strong>${item.suggestion}</p>
                ${diff.original_section ? `<p><strong>原文：</strong>${diff.original_section.substring(0, 100)}...</p>` : ''}
                ${diff.modified_section ? `<p><strong>修改为：</strong>${diff.modified_section.substring(0, 100)}...</p>` : ''}
            </div>
            <div class="review-item-actions">
                <label>
                    <input type="radio" name="review_${item.id}" value="approved" checked> 批准
                </label>
                <label>
                    <input type="radio" name="review_${item.id}" value="rejected"> 拒绝
                </label>
            </div>
            <textarea name="comment_${item.id}" placeholder="填写审核意见（可选）" rows="2"></textarea>
        `;
        
        reviewItems.appendChild(div);
    });
    
    reviewSection.style.display = 'block';
    
    document.getElementById('reviewForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const urlParams = new URLSearchParams(window.location.search);
        const taskId = urlParams.get('task_id');
        
        const reviews = [];
        needReview.forEach(item => {
            const approved = document.querySelector(`input[name="review_${item.id}"]:checked`).value === 'approved';
            const comment = document.querySelector(`textarea[name="comment_${item.id}"]`)?.value || '';
            
            reviews.push({
                evaluation_id: item.id,
                approved: approved,
                modified_suggestion: item.suggestion,
                comment: comment
            });
        });
        
        try {
            const response = await fetch(API_BASE + '/api/contracts/review', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: taskId,
                    reviews: reviews
                })
            });
            
            if (!response.ok) throw new Error('提交失败');
            
            alert('审核意见提交成功！');
            window.location.reload();
            
        } catch (error) {
            alert('提交失败: ' + error.message);
        }
    });
}
