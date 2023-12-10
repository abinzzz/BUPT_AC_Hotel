
document.getElementById('loginForm').addEventListener('submit', function(event) {
    // 获取用户名和密码的输入值
    var username = document.querySelector('input[name="user"]').value;
    var password = document.querySelector('input[name="pwd"]').value;

    // 检查用户名和密码是否为空
    if (username === '' || password === '') {
        // 阻止表单的默认提交行为
        event.preventDefault();

        // 获取或创建错误消息元素
        var errorMsg = document.querySelector('.error-msg');
        if (!errorMsg) {
            errorMsg = document.createElement('div');
            errorMsg.classList.add('error-msg');
            this.appendChild(errorMsg);
        }

        // 设置错误消息并显示
        errorMsg.textContent = '用户名和密码不能为空';
        errorMsg.style.color = 'red';
        errorMsg.style.marginTop = '10px';
    }
});
