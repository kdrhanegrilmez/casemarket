const API_BASE_URL =(
    import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\$/,'')

//Sepetteki ürünleri fastapiye göndererek siparii oluştur

export async function createOrder(token,items){

    const response = await fetch(`${API_BASE_URL}/api/orders`,{
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body : JSON.stringify({
            items:items,
        }),
    })

    const data = await response.json()

    if(!response.ok){
        const message =
            typeof data.detail === 'string'
                ? data.detail
                    :"Sipariş oluşturulamadı"

        throw new Error(message)
    }

    return data

}

export async function getMyOrders(token){

    const response = await fetch(`${API_BASE_URL}/api/orders/mine`,{
        method:'GET',
        headers:{
            Authorization: `Bearer ${token}`,
        },
    })

    const data = await response.json()

    if (!response.ok){
        const message=
            typeof data.detail ==='string'
                ? data.detail
                :'Sipariş geçmişi yüklenemedi'

        throw new Error(message)
    }

    return data

}
