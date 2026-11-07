document.addEventListener('DOMContentLoaded', () => {
    carregarUnidades();
    configurarFormulario();
});

// Buscar a lista de unidades cadastradas no backend
async function carregarUnidades() {
    const selectUnidade = document.getElementById('select-unidade');
    if (!selectUnidade) return;

    try {
        const response = await fetch('/api/unidades');
        const unidades = await response.json();

        selectUnidade.innerHTML = '<option value="">Selecione uma unidade...</option>';
        unidades.forEach(u => {
            const option = document.createElement('option');
            option.value = u.id;
            option.textContent = u.nome;
            selectUnidade.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar unidades:', error);
    }
}

// Lógica de envio do formulário de solicitação
function configurarFormulario() {
    const form = document.getElementById('form-solicitacao');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const unidadeId = document.getElementById('select-unidade').value;
        const responsavel = document.getElementById('input-responsavel').value;
        const obsGerais = document.getElementById('input-obs').value;

        // Coletar itens com quantidade maior que 0
        const itens = [];
        const inputsProdutos = document.querySelectorAll('.input-qtd');
        
        inputsProdutos.forEach(input => {
            const quantidade = parseFloat(input.value);
            if (quantidade > 0) {
                itens.push({
                    produto: input.dataset.produto,
                    categoria: input.dataset.categoria,
                    unidade_medida: input.dataset.medida,
                    quantidade: quantidade,
                    observacao: ''
                });
            }
        });

        if (itens.length === 0) {
            alert('Por favor, informe a quantidade de pelo menos um produto!');
            return;
        }

        const payload = {
            unidade_id: unidadeId,
            responsavel: responsavel,
            observacoes_gerais: obsGerais,
            itens: itens
        };

        try {
            const response = await fetch('/api/solicitacoes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const resultado = await response.json();

            if (response.ok) {
                alert(`Solicitação enviada com sucesso!\nProtocolo: ${resultado.protocolo}`);
                form.reset();
            } else {
                alert(`Erro: ${resultado.error}`);
            }
        } catch (error) {
            console.error('Erro na requisição:', error);
            alert('Falha ao enviar solicitação. Verifique a conexão com o servidor.');
        }
    });
}