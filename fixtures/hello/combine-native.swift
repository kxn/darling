import Combine
@_silgen_name("combine_native_owner") func combineNativeOwner() -> Int32
precondition(combineNativeOwner() == 1)
print("NATIVE_COMBINE_CORE_SEMANTICS_BEGIN")

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

struct TypedPayload: Equatable { let number: Int; let text: String; let fraction: Double }
@inline(never) func checkTypedJust<T: Equatable>(_ output: T) {
    let publisher: Result<T, ProbeError>.Publisher = Just(output).setFailureType(to: ProbeError.self)
    switch publisher.result { case .success(let value): precondition(value == output); case .failure: preconditionFailure("Just produced failure") }
    var received: [T] = []; var finished = 0
    let token = publisher.sink(receiveCompletion: { completion in
        switch completion { case .finished: finished += 1; case .failure: preconditionFailure("Just sent failure") }
    }, receiveValue: { received.append($0) })
    precondition(received == [output] && finished == 1)
    withExtendedLifetime(token) {}
}
for value in [Int.min, -1, 0, 1, Int.max] { checkTypedJust(value) }
for value in ["", "Linux", "Darling 真正的 Combine 🙂", String(repeating: "long-", count: 128)] { checkTypedJust(value) }
checkTypedJust(TypedPayload(number: 73, text: "owned payload", fraction: 1.25))
print("NATIVE_COMBINE_JUST_SET_FAILURE_TYPE_REAL_RESULT_PUBLISHER_GENERIC_VALUES_OK cases=10")

final class LifetimeValue { static var live = 0; init(){Self.live += 1}; deinit{Self.live -= 1} }
@inline(never) func checkReferenceLifetime() {
 let object = LifetimeValue(); let publisher = Just(object).setFailureType(to: ProbeError.self)
 var received: LifetimeValue?; let token = publisher.sink(receiveCompletion: { _ in }, receiveValue: { received = $0 })
 precondition(received === object && LifetimeValue.live == 1); withExtendedLifetime(token) {}
}
checkReferenceLifetime();precondition(LifetimeValue.live == 0)
print("NATIVE_COMBINE_REFERENCE_PAYLOAD_OWNERSHIP_OK")
var failureCount=0
let resultToken = Result<Int,ProbeError>.failure(.expected).publisher.sink(receiveCompletion:{ completion in if case .failure(.expected)=completion { failureCount += 1 } },receiveValue:{ _ in preconditionFailure("failure emitted value") })
precondition(failureCount == 1);withExtendedLifetime(resultToken){}
print("NATIVE_COMBINE_ORIGINAL_SDK_CORE_AND_TYPED_RESULT_ALL_OK")

@inline(never) func checkSourceControlChain(_ input:Int, throwsError:Bool) {
 var values:[String]=[];var completions=0;var failures=0;var innerCalls=0
 var storage=Set<AnyCancellable>()
 Just(input).setFailureType(to:ProbeError.self)
  .tryMap { value -> Int in if throwsError { throw ProbeError.expected }; return value * 3 }
  .flatMap(maxPublishers:.max(2)) { value -> Result<String,Error>.Publisher in innerCalls += 1;return Just("value=\(value)").setFailureType(to:Error.self) }
  .eraseToAnyPublisher()
  .sink(receiveCompletion:{ completion in
   switch completion {case .finished:completions += 1;case .failure(let error):precondition(error is ProbeError);failures += 1}
  },receiveValue:{values.append($0)}).store(in:&storage)
 precondition(storage.count==1)
 if throwsError {precondition(values.isEmpty && failures==1 && completions==0 && innerCalls==0)}
 else {precondition(values==["value=\(input*3)"] && completions==1 && failures==0 && innerCalls==1)}
 storage.removeAll()
}
for i in 0..<32 {checkSourceControlChain(i,throwsError:false);checkSourceControlChain(i,throwsError:true)}
print("NATIVE_COMBINE_XCSOURCECONTROL_TYPED_TRYMAP_FLATMAP_ERASURE_STORE_SUCCESS_FAILURE_OK cases=64")

final class PublishedModel:ObservableObject {@Published var value=4}
let publishedModel=PublishedModel();var publishedValues:[Int]=[];var willChanges=0
let publishedToken=publishedModel.$value.sink{publishedValues.append($0)}
let willToken=publishedModel.objectWillChange.sink{willChanges += 1}
publishedModel.value=9;publishedModel.value=16
precondition(publishedValues==[4,9,16] && willChanges==2)
publishedToken.cancel();willToken.cancel();publishedModel.value=25
precondition(publishedValues==[4,9,16] && willChanges==2)
print("NATIVE_COMBINE_PUBLISHED_REFLECTION_OBSERVABLE_OBJECT_CHANGE_AND_CANCEL_OK")
print("NATIVE_COMBINE_ALL_CHECKED_SEMANTICS_OK")
