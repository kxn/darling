import Combine

enum ProbeError: Error { case expected }
var values: [Int] = []
var completed = false
let mapped = Just(7).map { $0 * 6 }.eraseToAnyPublisher()
let mapToken = mapped.sink(receiveCompletion: { _ in completed = true },
                           receiveValue: { values.append($0) })
precondition(values == [42] && completed)

var recovered = 0
let catchToken = Fail<Int, ProbeError>(error: .expected)
    .catch { _ in Just(23) }.sink { recovered = $0 }
precondition(recovered == 23)

var promise: Future<Int, ProbeError>.Promise?
let future = Future<Int, ProbeError> { promise = $0 }
var futureValues: [Int] = []
let futureToken = future.sink(receiveCompletion: { _ in },
                              receiveValue: { futureValues.append($0) })
precondition(futureValues.isEmpty)
promise!(.success(99))
precondition(futureValues == [99])

final class DemandProbe: Subscriber {
    typealias Input = Int
    typealias Failure = Never
    var subscription: Subscription?
    var values: [Int] = []
    var finished = false
    func receive(subscription: Subscription) {
        self.subscription = subscription
        subscription.request(.max(1))
    }
    func receive(_ input: Int) -> Subscribers.Demand {
        values.append(input)
        return .none
    }
    func receive(completion: Subscribers.Completion<Never>) { finished = true }
}
let subject = PassthroughSubject<Int, Never>()
let subscriber = DemandProbe()
subject.subscribe(subscriber)
subject.send(1)
subject.send(2)
precondition(subscriber.values == [1])
subscriber.subscription!.request(.max(1))
subject.send(3)
precondition(subscriber.values == [1, 3])
subscriber.subscription!.cancel()
subject.send(4)
precondition(subscriber.values == [1, 3])

var closureValues: [Int] = []
let erasedSubscriber = AnySubscriber<Int, Never>(
    receiveSubscription: { $0.request(.unlimited) },
    receiveValue: { closureValues.append($0); return .none },
    receiveCompletion: { _ in })
Just(5).subscribe(erasedSubscriber)
precondition(closureValues == [5])
withExtendedLifetime([mapToken, catchToken, futureToken]) {}
print("COMBINE_MAP_CATCH_FUTURE_DEMAND_CANCEL_OK")
